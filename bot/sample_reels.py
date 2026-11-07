"""Make the 3 sample reels for review (Sat athar, Sun verse+tafsir, Thu shareable dua).
All texts are pulled from the repo's sources and asserted, never typed from memory."""
import json
import re
from pathlib import Path

import yaml

import adhkar
import captions
from quran import verse
from reel_maker import make_reel

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "media" / "reels" / "samples"


def saddi_sentence(key, start_marker, end_marker):
    """Exact substring of As-Sa'di (quran.com API, tafsir id 91) between two markers."""
    raw = json.loads((ROOT / "data" / "tafsir" / f"saddi_{key.replace(':', '_')}.json").read_text(encoding="utf-8"))
    text = re.sub(r"<[^>]+>", "", raw["tafsir"]["text"])
    i = text.index(start_marker)
    j = text.index(end_marker, i) + len(end_marker)
    return text[i:j]


def main():
    athar = {a["num"]: a for a in yaml.safe_load((ROOT / "data" / "athar.yaml").read_text(encoding="utf-8"))}
    items = []

    # 1) Saturday — أثر اليوم (soft ambience)
    a = athar[2040]
    parts = [p.strip() for p in re.split(r"(?<=لحده)\s", a["text"], maxsplit=1)]
    make_reel(OUT / "sample1_athar.mp4", parts, title="أثر اليوم", bottom=f"{a['title']}\n{a['source']}",
              audio="ambience", duration=10)
    items.append({"file": "sample1_athar.mp4", "theme": "athar", "day": "السبت",
                  "text": a["text"], "source": a["source"], "audio": "صوت طبيعة هادئ (مولَّد محلياً، بدون حقوق)",
                  "caption": captions.share_caption("athar", 0, a["title"])})

    # 2) Sunday — verse + one line of As-Sa'di (silence until a licensed recitation is chosen)
    txt, src = verse(13, 28)
    # Quran text is NEVER reordered: the whole verse (in order) is the hook, visible from frame 0;
    # only the tafsir line is revealed.
    tafsir = saddi_sentence("13:28", "حقيق بها", "سوى ذكره")
    make_reel(OUT / "sample2_verse.mp4", [txt], title=src, sub=f"قال السعدي: «{tafsir}»",
              bottom="تفسير السعدي · تيسير الكريم الرحمن", audio="silence", duration=11, px=62)
    items.append({"file": "sample2_verse.mp4", "theme": "verse", "day": "الأحد",
                  "text": txt, "tafsir": tafsir, "source": f"{src} · تفسير السعدي (quran.com API، tafsir 91)",
                  "audio": "صمت (التلاوة تنتظر مصدر بترخيص واضح)",
                  "caption": captions.share_caption("verse", 1, src)})

    # 3) Thursday — shareable dua for the deceased (Hisn al-Muslim 159)
    d = next(x for x in adhkar.dead_duas() if x["hisn_id"] == 159)
    dlines = d["main"].split("\n")
    make_reel(OUT / "sample3_dua.mp4", dlines, title="دعاء للميت", bottom="حصن المسلم ١٥٩",
              audio="silence", duration=11, weight=400, px=60)
    items.append({"file": "sample3_dua.mp4", "theme": "dua_deceased", "day": "الخميس",
                  "text": d["main"], "source": "حصن المسلم ١٥٩ (الدعاء للميت في الصلاة عليه)",
                  "audio": "صمت", "caption": captions.share_caption("dua_deceased", 2, "لا تنسوا موتاكم من الدعاء")})

    (OUT / "samples.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(i["file"] for i in items))


if __name__ == "__main__":
    main()
