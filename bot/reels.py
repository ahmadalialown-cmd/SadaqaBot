"""Reels helper: drop a video into reels_inbox/ named by its verse, e.g.
   reels_inbox/51-17.mp4        (sura 51, ayah 17)
   reels_inbox/2-285-286.mp4    (ayat 285..286)
then run:  python bot/reels.py [--time "2026-11-20 20:00"]
Each video is letterboxed to 1080x1920 on the account's background colour, the verse
(from the Tanzil text) is overlaid in the account style, and a REELS item is queued in the
bank as "pending" (it still needs approval).
"""
import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

from prayer import TZ
from quran import verse
from render import STYLE, _font_data_uri

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "reels_inbox"
OUTDIR = ROOT / "media" / "reels"
BANK = ROOT / "data" / "bank.json"

OVERLAY = """<!doctype html><html dir="rtl"><head><meta charset="utf-8"><style>
@font-face {{ font-family:'Q'; src:url('{qf}'); }} @font-face {{ font-family:'M'; src:url('{mf}'); }}
html,body {{ margin:0; width:1080px; height:1920px; background:transparent; }}
.top {{ position:absolute; top:150px; left:90px; right:90px; text-align:center; color:{fg}; }}
.v {{ font-family:'Q','M',serif; font-size:{px}px; line-height:2.1; text-shadow:0 2px 6px rgba(0,0,0,.25); }}
.s {{ font-family:'M',serif; font-size:30px; color:{muted}; margin-top:18px; }}
</style></head><body><div class="top"><div class="v">{text}</div><div class="s">{src}</div></div></body></html>"""


def overlay_png(text, src, path):
    px = 60 if len(text) < 120 else 50 if len(text) < 250 else 42
    html = OVERLAY.format(qf=_font_data_uri(STYLE["quran_font_file"]), mf=_font_data_uri(STYLE["font_file"]),
                          fg=STYLE["fg"], muted=STYLE["muted"], px=px, text=text, src=src)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.set_content(html)
        pg.evaluate("document.fonts.ready")
        pg.screenshot(path=str(path), omit_background=True)
        b.close()


def make_reel(video: Path, out: Path, text, src):
    ov = out.with_suffix(".overlay.png")
    overlay_png(text, src, ov)
    bg = STYLE["bg"].lstrip("#")
    vf = (f"[0:v]scale=1080:-2:force_original_aspect_ratio=decrease,"
          f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x{bg},setsar=1[base];[base][1:v]overlay=0:0")
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-i", str(ov), "-filter_complex", vf,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-t", "90", str(out)],
                   check=True)
    ov.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", help='"YYYY-MM-DD HH:MM" (Doha). Default: tomorrow 20:00')
    a = ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    when = (datetime.strptime(a.time, "%Y-%m-%d %H:%M").replace(tzinfo=TZ) if a.time else
            (datetime.now(TZ) + timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0))
    for v in sorted(INBOX.glob("*.mp4")) + sorted(INBOX.glob("*.mov")):
        m = re.fullmatch(r"(\d+)-(\d+)(?:-(\d+))?", v.stem)
        if not m:
            print(f"skip {v.name}: name it like 51-17.mp4")
            continue
        s, a1, a2 = int(m[1]), int(m[2]), int(m[3] or m[2])
        text, src = verse(s, a1, a2)
        rid = f"{when:%Y-%m-%d}-reel-{s}-{a1}-{a2}"
        out = OUTDIR / f"{rid}.mp4"
        make_reel(v, out, text, src)
        bank["items"].append({
            "id": rid, "date": f"{when:%Y-%m-%d}", "slot": "reel", "kind": "reel",
            "time": when.isoformat(), "title": "", "main": text, "note": None, "source": src,
            "refs": [f"quran:{s}:{a1}-{a2}"], "video": f"media/reels/{rid}.mp4",
            "caption": f"{src}\n\nصدقة جارية عن سعود القحطاني، رحمه الله.", "status": "pending"})
        done = INBOX / "done"
        done.mkdir(exist_ok=True)
        shutil.move(str(v), done / v.name)
        print(f"queued {rid} (pending approval)")
        when += timedelta(days=1)
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
