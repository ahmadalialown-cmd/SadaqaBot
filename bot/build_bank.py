"""Build/extend the content bank (data/bank.json) for N days.

Every item is created with status "pending"; only "approved" items are ever published.
Existing items (and their status) are never overwritten.
Usage: python bot/build_bank.py [--start YYYY-MM-DD] [--days 90]
"""
import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

import adhkar
import captions
from prayer import TZ, times
from quran import verse

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data" / "bank.json"


def load_cfg():
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def load_bank():
    if BANK.exists():
        return json.loads(BANK.read_text(encoding="utf-8"))
    return {"items": []}


def save_bank(bank):
    bank["items"].sort(key=lambda x: (x["time"], x["id"]))
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")


def at(d: date, hhmm: str):
    h, m = map(int, hhmm.split(":"))
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)


def items_for_day(d: date, n: int, cfg, verses, hadith, duas):
    """n = day index since the bank's epoch (drives rotation)."""
    t = times(d)
    out = []
    sessions = [
        ("morning", "أذكار الصباح", t["fajr"] + timedelta(minutes=cfg["morning_after_fajr_min"])),
        ("evening", "أذكار المساء", t["asr"] + timedelta(minutes=cfg["evening_after_asr_min"])),
        ("sleep", "أذكار النوم", at(d, cfg["sleep_time"])),
    ]
    for key, title, when in sessions:
        pool = adhkar.items(key)
        k = cfg["frames_per_story"][key]
        for f in range(k):
            it = pool[(n * k + f) % len(pool)]
            out.append({
                "id": f"{d}-{key}-{f + 1}", "date": str(d), "slot": f"story_{key}", "kind": "story",
                "time": (when + timedelta(minutes=f)).isoformat(), "title": title,
                "main": it["main"], "note": it["count"], "source": it["source"],
                "refs": [f"hisn:{it['hisn_id']}"], "caption": "", "status": "pending",
            })

    is_friday = d.weekday() == 4
    maghrib = t["maghrib"]
    if is_friday:
        fri_n = n // 7
        # Asr on Friday: الصلاة على النبي ﷺ (verse and hadith alternate)
        if fri_n % 2 == 0:
            txt, src = verse(33, 56)
            asr_item = {"title": "الصلاة على النبي ﷺ", "main": txt, "source": src, "refs": ["quran:33:56"]}
        else:
            h = next(x for x in hadith if x["id"] == "muslim-408")
            asr_item = {"title": h["title"], "main": h["text"], "source": h["source"], "refs": [f"hadith:{h['id']}"]}
        out.append({
            "id": f"{d}-friday-asr", "date": str(d), "slot": "feed_friday_asr", "kind": "feed",
            "time": (t["asr"] + timedelta(minutes=cfg["friday_asr_post_after_min"])).isoformat(),
            "note": None, **asr_item,
            "caption": captions.friday_salawat(asr_item, cfg), "status": "pending",
        })
        dua = duas[fri_n % len(duas)]
        feed = {"title": f"{cfg['deceased_name']} · رحمه الله", "main": dua["main"],
                "source": dua["source"], "refs": [f"hisn:{dua['hisn_id']}"]}
        cap = captions.dua_deceased(feed, cfg)
        slot = "feed_dua_deceased"
    elif n % 10 == 4:
        h = hadith[(n // 10) % len(hadith)]
        feed = {"title": h["title"], "main": h["text"], "source": h["source"], "refs": [f"hadith:{h['id']}"]}
        cap = captions.hadith(feed, cfg)
        slot = "feed_hadith"
    else:
        s, a, b, title = verses[n % len(verses)]
        txt, src = verse(s, a, b)
        feed = {"title": title, "main": txt, "source": src, "refs": [f"quran:{s}:{a}-{b}"]}
        cap = captions.verse(feed, cfg)
        slot = "feed_verse"
    out.append({"id": f"{d}-maghrib", "date": str(d), "slot": slot, "kind": "feed",
                "time": maghrib.isoformat(), "note": None, **feed, "caption": cap, "status": "pending"})
    return out


def build(start: date, days: int):
    cfg = load_cfg()
    verses = yaml.safe_load((ROOT / "data" / "verses.yaml").read_text(encoding="utf-8"))
    hadith = yaml.safe_load((ROOT / "data" / "hadith.yaml").read_text(encoding="utf-8"))
    duas = adhkar.dead_duas()
    bank = load_bank()
    epoch = date.fromisoformat(bank.setdefault("epoch", str(start)))
    have = {x["id"] for x in bank["items"]}
    added = 0
    for i in range(days):
        d = start + timedelta(days=i)
        for it in items_for_day(d, (d - epoch).days, cfg, verses, hadith, duas):
            if it["id"] not in have:
                bank["items"].append(it)
                added += 1
    save_bank(bank)
    return added, len(bank["items"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=str(datetime.now(TZ).date() + timedelta(days=1)))
    ap.add_argument("--days", type=int, default=90)
    a = ap.parse_args()
    added, total = build(date.fromisoformat(a.start), a.days)
    print(f"added {added}, total {total}")
