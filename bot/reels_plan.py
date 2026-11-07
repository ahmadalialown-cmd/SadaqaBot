"""Daily reel plan (specs go into the bank; videos are rendered on review/approval).

Weekly rotation (Doha weekdays):
  Sat/Mon/Wed  أثر اليوم (same athar as that day's Maghrib post), soft ambience / silence
  Sun/Tue      short verse + one line of As-Sa'di (silence until a licensed recitation exists)
  Thu          shareable dua (deceased / sick / parents), silence
  Fri          Friday reminder + dua for Saud (the Friday dua), silence
Hijri seasons (data/reels_content.yaml `seasons`) replace the rotation automatically.
"""
import json
import re
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import yaml
from hijridate import Gregorian

import adhkar
import captions
from prayer import TZ
from quran import title_for, verse

ROOT = Path(__file__).resolve().parents[1]
SAT, SUN, MON, TUE, WED, THU, FRI = 5, 6, 0, 1, 2, 3, 4


@lru_cache
def content():
    return yaml.safe_load((ROOT / "data" / "reels_content.yaml").read_text(encoding="utf-8"))


def saddi(sura, ayah, start, end):
    """Exact substring of As-Sa'di between two markers (raises if not found)."""
    raw = json.loads((ROOT / "data" / "tafsir" / f"saddi_{sura}_{ayah}.json").read_text(encoding="utf-8"))
    text = re.sub(r"<[^>]+>", "", raw["tafsir"]["text"])
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[i:j]


def hisn_item(chapter, item):
    data = json.loads((ROOT / "data" / "hisn" / f"{chapter}.json").read_text(encoding="utf-8-sig"))
    it = next(x for x in list(data.values())[0] if x["ID"] == item)
    main, note = adhkar._clean(it["ARABIC_TEXT"])
    return adhkar.split_lines(main), note


def season_of(d: date):
    h = Gregorian(d.year, d.month, d.day).to_hijri()
    for name, s in content()["seasons"].items():
        r = s["hijri"]
        if h.month == r["month"] and r["from"] <= h.day <= r["to"]:
            return name, h
    return None, h


def _when(d, hhmm):
    h, m = map(int, hhmm.split(":"))
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)


def _weekday_count(epoch, d, days):
    return sum(1 for i in range((d - epoch).days) if (epoch + timedelta(days=i)).weekday() in days)


def reel_for_day(d: date, epoch: date, cfg, athar_today, friday_dua):
    """-> dict spec for the day's main reel, or None."""
    n = (d - epoch).days
    wd = d.weekday()
    season, h = season_of(d)
    if season:
        pool = content()["seasons"][season]["verses"]
        s, a, b = pool[(h.day - 1) % len(pool)]
        txt, src = verse(s, a, b)
        return {"type": f"season_{season}", "theme": "verse", "lines": [txt], "title": src,
                "bottom": "", "audio": "silence", "weight": 500, "refs": [f"quran:{s}:{a}-{b}"],
                "needs_review": True, "lead": src}
    if wd in (SAT, MON, WED):
        if not athar_today:
            return None
        return {"type": "athar", "theme": "athar", "lines": [athar_today["main"]], "title": "أثر اليوم",
                "bottom": f"{athar_today['title']}\n{athar_today['source']}",
                "audio": "ambience" if n % 2 == 0 else "silence", "weight": 500,
                "refs": athar_today["refs"], "lead": athar_today["title"]}
    if wd in (SUN, TUE):
        pool = content()["verse_tafsir"]
        s, a, st, en = pool[_weekday_count(epoch, d, (SUN, TUE)) % len(pool)]
        txt, src = verse(s, a)
        return {"type": "verse_tafsir", "theme": "verse", "lines": [txt], "title": src,
                "sub": f"قال السعدي: «{saddi(s, a, st, en)}»", "bottom": "تفسير السعدي · تيسير الكريم الرحمن",
                "audio": "silence", "weight": 500, "px": 62,
                "refs": [f"quran:{s}:{a}", f"saddi:{s}:{a}"], "lead": src}
    if wd == THU:
        pool = content()["share_duas"]
        p = pool[_weekday_count(epoch, d, (THU,)) % len(pool)]
        if p["kind"] == "hisn":
            text, note = hisn_item(p["chapter"], p["item"])
            src = f"حصن المسلم {str(p['item']).translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))}"
            if note:
                src = f"{note}\n{src}"
            ref = f"hisn:{p['item']}"
        else:
            s, a, b = p["ref"]
            text, src = verse(s, a, b)
            ref = f"quran:{s}:{a}-{b}"
        return {"type": "share_dua", "theme": p["theme"], "lines": [text], "title": p["title"],
                "bottom": src, "audio": "silence", "weight": 400, "px": 60, "refs": [ref],
                "lead": {"dua_deceased": "لا تنسوا موتاكم من الدعاء", "dua_sick": "لكل مريض تحبه",
                         "dua_parents": "لوالديك، أحياءً وأمواتاً"}[p["theme"]]}
    if wd == FRI and friday_dua:
        return {"type": "friday", "theme": "friday", "lines": [friday_dua["main"]],
                "title": f"يوم الجمعة · {cfg['deceased_name']} رحمه الله", "bottom": friday_dua["source"],
                "audio": "silence", "weight": 400, "px": 56, "duration": 12, "refs": friday_dua["refs"],
                "lead": f"في يوم الجمعة… ادعوا لـ{cfg['deceased_name']} رحمه الله"}
    return None


def bank_items(d: date, epoch: date, cfg, day_items):
    """Reel bank items for date d. day_items = the other items already built for that day."""
    athar_today = next((x for x in day_items if x["slot"] == "feed_athar"), None)
    friday_dua = next((x for x in day_items if x["slot"] == "feed_dua_deceased"), None)
    spec = reel_for_day(d, epoch, cfg, athar_today, friday_dua)
    if not spec:
        return []
    n = (d - epoch).days
    rid = f"{d}-reel-1"
    item = {
        "id": rid, "date": str(d), "slot": f"reel_{spec['type']}", "kind": "reel",
        "time": _when(d, cfg.get("reel_time", "20:30")).isoformat(),
        "title": spec["title"], "main": "\n".join(spec["lines"]), "note": None,
        "source": spec["bottom"].replace("\n", " · ") if spec.get("bottom") else spec["title"],
        "video": f"media/reels/{rid}.mp4", "reel_spec": spec, "theme": spec["theme"],
        "refs": spec["refs"], "caption": captions.share_caption(spec["theme"], n, spec.get("lead", "")),
        "status": "pending",
    }
    out = [item]
    if cfg.get("reels_per_day", 1) >= 2 and athar_today and spec["type"] != "athar":
        # optional 2nd reel: the athar of the day
        s2 = {"type": "athar", "theme": "athar", "lines": [athar_today["main"]], "title": "أثر اليوم",
              "bottom": f"{athar_today['title']}\n{athar_today['source']}", "audio": "silence",
              "weight": 500, "refs": athar_today["refs"], "lead": athar_today["title"]}
        rid2 = f"{d}-reel-2"
        out.append({**item, "id": rid2, "slot": "reel_athar", "theme": "athar",
                    "time": _when(d, cfg.get("reel_time_2", "13:00")).isoformat(),
                    "title": s2["title"], "main": athar_today["main"], "source": athar_today["source"],
                    "video": f"media/reels/{rid2}.mp4", "reel_spec": s2, "refs": s2["refs"],
                    "caption": captions.share_caption("athar", n + 1, s2["lead"])})
    return out


def render_reel(item):
    """Render the item's video from its spec (idempotent)."""
    from reel_maker import make_reel
    out = ROOT / item["video"]
    if out.exists():
        return out
    s = item["reel_spec"]
    return make_reel(out, s["lines"], title=s.get("title"), sub=s.get("sub"), bottom=s.get("bottom"),
                     duration=s.get("duration", 11 if s.get("sub") else 10), audio=s.get("audio", "silence"),
                     weight=s.get("weight", 500), px=s.get("px", 64))
