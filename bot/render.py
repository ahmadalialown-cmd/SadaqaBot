"""Render posts/stories to PNG with HTML/CSS + Playwright (Chromium does Arabic shaping)."""
import base64
import html
from functools import lru_cache
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"

SIZES = {"feed": (1080, 1350), "story": (1080, 1920)}

# Style tokens (tuned against the account's real posts; see style_refs/ comparison)
STYLE = {
    "bg": "#6E6459",
    "fg": "#F1E9DD",
    "muted": "rgba(241,233,221,.72)",
    "font": "Amiri",
    "font_file": "Amiri-Regular.ttf",
    "quran_font_file": "AmiriQuran-Regular.ttf",  # handles Uthmani marks properly
}

TEMPLATE = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<style>
@font-face {{ font-family: 'Main'; src: url('{font_url}'); }}
@font-face {{ font-family: 'Quran'; src: url('{quran_font_url}'); }}
.main.q {{ font-family: 'Quran', 'Main', serif; line-height:2.2; }}
html, body {{ margin:0; width:{w}px; height:{h}px; background:{bg}; }}
body {{ display:flex; align-items:center; justify-content:center; font-family:'Main', serif;
        color:{fg}; text-align:center; -webkit-font-smoothing:antialiased; }}
.wrap {{ width:{inner}px; display:flex; flex-direction:column; align-items:center; gap:{gap}px; }}
.title {{ font-size:{title_px}px; color:{muted}; letter-spacing:0; }}
.rule {{ width:90px; height:1.5px; background:{muted}; opacity:.7; }}
.main {{ font-size:{main_px}px; line-height:1.9; }}
.source {{ font-size:{src_px}px; color:{muted}; }}
.quote {{ font-size:{quote_px}px; line-height:1.8; margin-top:{gap}px; }}
.note {{ font-size:{src_px}px; color:{muted}; margin-top:-{half_gap}px; }}
</style></head><body><div class="wrap" id="wrap">
{title_html}<div class="main{main_cls}" id="main">{main}</div>{note_html}{source_html}{quote_html}
</div>
<script>
// shrink the main text until everything fits the safe area
(function () {{
  var wrap = document.getElementById('wrap'), main = document.getElementById('main');
  var px = {main_px}, maxH = {max_h};
  function fit() {{
    while (wrap.scrollHeight > maxH && px > 26) {{ px -= 2; main.style.fontSize = px + 'px'; }}
  }}
  document.fonts.ready.then(fit); fit();
}})();
</script></body></html>"""


@lru_cache
def _font_data_uri(name: str) -> str:
    # set_content pages are about:blank, which can't load file:// fonts, so inline it
    return "data:font/ttf;base64," + base64.b64encode((FONTS / name).read_bytes()).decode()


def _fit_main_px(text: str, kind: str) -> int:
    n = len(text)
    base = 64 if kind == "feed" else 68
    if n > 120: base -= 8
    if n > 220: base -= 8
    if n > 350: base -= 8
    if n > 500: base -= 6
    return base


def build_html(kind, main, title=None, source=None, quote=None, quote_source=None, note=None):
    w, h = SIZES[kind]
    esc = lambda s: html.escape(s or "").replace("\n", "<br>")
    title_html = f'<div class="title">{esc(title)}</div><div class="rule"></div>' if title else ""
    source_html = f'<div class="source">{esc(source)}</div>' if source else ""
    note_html = f'<div class="note">{esc(note)}</div>' if note else ""
    quote_html = ""
    if quote:
        quote_html = f'<div class="quote">{esc(quote)}</div>'
        if quote_source:
            quote_html += f'<div class="source">{esc(quote_source)}</div>'
    main_px = _fit_main_px(main, kind)
    return TEMPLATE.format(
        font_url=_font_data_uri(STYLE["font_file"]),
        quran_font_url=_font_data_uri(STYLE["quran_font_file"]),
        main_cls=" q" if (source or "").startswith("سورة") else "", w=w, h=h,
        bg=STYLE["bg"], fg=STYLE["fg"], muted=STYLE["muted"],
        inner=int(w * (0.80 if kind == "feed" else 0.78)), gap=34, half_gap=17,
        title_px=34, main_px=main_px, src_px=28, quote_px=int(main_px * 0.7),
        # feed: keep a calm margin; story: stay inside the central safe area (no UI overlap)
        max_h=int(h * (0.84 if kind == "feed" else 0.70)),
        title_html=title_html, main=esc(main), note_html=note_html,
        source_html=source_html, quote_html=quote_html)


def render(items, out_dir: Path):
    """items: list of dicts with id, kind, main, title?, source?, quote?, quote_source?"""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for it in items:
            w, h = SIZES[it["kind"]]
            page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            page.set_content(build_html(it["kind"], it["main"], it.get("title"), it.get("source"),
                                        it.get("quote"), it.get("quote_source"), it.get("note")))
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(50)
            path = out_dir / f"{it['id']}.png"
            page.screenshot(path=str(path), full_page=False)
            page.close()
            paths.append(path)
        b.close()
    return paths


if __name__ == "__main__":
    # Render given bank ids (or the first few items) into out/
    import json
    import sys
    bank = json.loads((ROOT / "data" / "bank.json").read_text(encoding="utf-8"))["items"]
    want = set(sys.argv[1:])
    sel = [x for x in bank if x["id"] in want] if want else bank[:12]
    for p in render(sel, ROOT / "out"):
        print(p.name)
