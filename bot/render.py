"""Render posts/stories to PNG with HTML/CSS + Playwright (Chromium does Arabic shaping).

Layout matches the account's own slides (checked 2026-11-07 on @9d8h0garyh):
small muted title at the top + short thin rule, main text centred with one clause per
line, small muted count/source line at the bottom, flat warm-taupe background.
"""
import base64
import html
from functools import lru_cache
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"

SIZES = {"feed": (1080, 1350), "story": (1080, 1920)}

STYLE = {
    "bg": "#6E6459",
    "fg": "#F3ECE2",
    "muted": "rgba(243,236,226,.62)",
    "font_file": "NotoNaskhArabic.ttf",   # variable weight; closest to the account's slides
    "weight": 600,
    "title_weight": 400,
}

TEMPLATE = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<style>
@font-face {{ font-family:'Main'; src:url('{font_url}'); font-weight:100 900; }}
html, body {{ margin:0; width:{w}px; height:{h}px; background:{bg}; overflow:hidden; }}
body {{ font-family:'Main', serif; color:{fg}; text-align:center; -webkit-font-smoothing:antialiased; }}
.top {{ position:absolute; left:0; right:0; top:{title_top}px; display:flex; flex-direction:column; align-items:center; }}
.title {{ font-size:{title_px}px; color:{muted}; font-weight:{title_weight}; }}
.rule {{ width:84px; height:1.5px; background:{muted}; opacity:.6; margin-top:22px; }}
.mid {{ position:absolute; left:{side}px; right:{side}px; top:{mid_top}px; bottom:{mid_bottom}px;
        display:flex; align-items:center; justify-content:center; }}
.main {{ font-size:{main_px}px; line-height:1.85; font-weight:{weight}; white-space:pre-line; }}
.bottom {{ position:absolute; left:0; right:0; bottom:{bottom}px; font-size:{src_px}px; color:{muted}; line-height:1.6; }}
</style></head><body>
<div class="top">{title_html}</div>
<div class="mid" id="mid"><div class="main" id="main">{main}</div></div>
<div class="bottom">{bottom_html}</div>
<script>
(function () {{
  var mid = document.getElementById('mid'), main = document.getElementById('main'), px = {main_px};
  function fit() {{
    while ((main.scrollHeight > mid.clientHeight || main.scrollWidth > mid.clientWidth) && px > 24) {{
      px -= 2; main.style.fontSize = px + 'px';
    }}
  }}
  document.fonts.ready.then(fit); fit();
}})();
</script></body></html>"""


@lru_cache
def _font_data_uri(name: str) -> str:
    # set_content pages are about:blank, which can't load file:// fonts, so inline it
    return "data:font/ttf;base64," + base64.b64encode((FONTS / name).read_bytes()).decode()


def build_html(kind, main, title=None, source=None, note=None, **_):
    w, h = SIZES[kind]
    esc = lambda s: html.escape(s or "")
    title_html = f'<div class="title">{esc(title)}</div><div class="rule"></div>' if title else ""
    bottom = [b for b in (note, source) if b]
    bottom_html = "<br>".join(esc(b) for b in bottom)
    story = kind == "story"
    # story: keep everything inside the central safe area (top/bottom ~250px have UI)
    return TEMPLATE.format(
        font_url=_font_data_uri(STYLE["font_file"]), w=w, h=h,
        bg=STYLE["bg"], fg=STYLE["fg"], muted=STYLE["muted"],
        weight=STYLE["weight"], title_weight=STYLE["title_weight"],
        title_top=320 if story else 110, title_px=52 if story else 48,
        mid_top=490 if story else 250, mid_bottom=460 if story else 180,
        side=70 if story else 60, bottom=320 if story else 90,
        main_px=70 if story else 66, src_px=30 if story else 28,
        title_html=title_html, main=esc(main), bottom_html=bottom_html)


def render(items, out_dir: Path):
    """items: dicts with id, kind, main, and optional title/source/note."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for it in items:
            w, h = SIZES[it["kind"]]
            doc = build_html(it["kind"], it["main"], it.get("title"),
                             it.get("source") if it.get("show_source", True) else None, it.get("note"))
            path = out_dir / f"{it['id']}.png"
            for attempt in range(3):  # Chromium occasionally fails a capture; retry on a fresh page
                page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                try:
                    page.set_content(doc)
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(60)
                    page.screenshot(path=str(path))
                    break
                except Exception:
                    if attempt == 2:
                        raise
                finally:
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
