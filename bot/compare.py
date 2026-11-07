"""Side-by-side: the account's real slides (style_refs/*.png) vs our renders of the same text.
Usage: python bot/compare.py  -> out/compare.png"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import adhkar
from render import render

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "style_refs"


def main():
    pool = adhkar.items("morning")
    pick = lambda hid, title=None: next(x for x in pool if x["hisn_id"] == hid and
                                        (title is None or x["title"] == title))
    mine = []
    for cid, hid, title in (("cmp_kursi", 75, None), ("cmp_ikhlas", 76, "سورة الإخلاص"), ("cmp_bika", 78, None)):
        x = pick(hid, title)
        mine.append({"id": cid, "kind": "feed", "main": x["main"], "title": x["title"],
                     "note": x["count"], "show_source": False})
    out = render(mine, ROOT / "out")
    refs = sorted(REFS.glob("ref_*.png"))
    rows = list(zip(refs, out))
    W = 540
    sheet = Image.new("RGB", (W * 2 + 30, (int(W * 1.25) + 50) * len(rows) + 10), "#222")
    d = ImageDraw.Draw(sheet)
    y = 10
    for ref, me in rows:
        for i, (label, p) in enumerate((("theirs", ref), ("ours", me))):
            im = Image.open(p).convert("RGB")
            im = im.resize((W, int(im.height * W / im.width)))
            sheet.paste(im, (10 + i * (W + 10), y + 30))
            d.text((10 + i * (W + 10), y + 8), f"{label}: {p.name}", fill="#ddd")
        y += int(W * 1.25) + 50
    sheet.save(ROOT / "out" / "compare.png")
    print("out/compare.png")


if __name__ == "__main__":
    sys.exit(main())
