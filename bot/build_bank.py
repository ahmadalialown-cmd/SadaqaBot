"""Build/extend the content bank (data/bank.json) for N days.

Per day:
- Stories: the account's own adhkar carousel slides (data/adhkar_frames.json, made by
  adhkar_stories.py) re-published as story frames: morning after Fajr, evening after Asr,
  sleep at 22:00.
- Feed at Maghrib: one أثر from كتاب الزهد للإمام أحمد (data/athar.yaml), no repeats.
- Friday: Asr post on الصلاة على النبي ﷺ, and the Maghrib post is a dua for سعود (unchanged).

Every item is created "pending"; only "approved" items are ever published.
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
SESSIONS_AR = {"morning": "أذكار الصباح", "evening": "أذكار المساء", "sleep": "أذكار النوم"}


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


def non_friday_index(epoch: date, d: date) -> int:
    return sum(1 for i in range((d - epoch).days) if (epoch + timedelta(days=i)).weekday() != 4)


def items_for_day(d: date, epoch: date, cfg, athar, hadith, duas, frames):
    t = times(d)
    n = (d - epoch).days
    out = []
    when = {
        "morning": t["fajr"] + timedelta(minutes=cfg["morning_after_fajr_min"]),
        "evening": t["asr"] + timedelta(minutes=cfg["evening_after_asr_min"]),
        "sleep": at(d, cfg["sleep_time"]),
    }
    for key, info in frames.items():
        for i, img in enumerate(info["frames"], 1):
            out.append({
                "id": f"{d}-{key}-{i:02d}", "date": str(d), "slot": f"story_{key}", "kind": "story",
                "time": when[key].isoformat(), "title": SESSIONS_AR[key],
                "main": f"شريحة {i} من {len(info['frames'])}", "note": None,
                "source": f"منشورك «{SESSIONS_AR[key]}»", "image": img,
                "refs": [f"ig:{info['post_id']}#{i}"], "caption": "", "status": "pending",
            })

    if d.weekday() == 4:  # Friday — unchanged
        fri_n = n // 7
        if fri_n % 2 == 0:
            txt, src = verse(33, 56)
            asr_item = {"title": "الصلاة على النبي ﷺ", "main": txt, "source": src, "refs": ["quran:33:56"]}
        else:
            h = next(x for x in hadith if x["id"] == "muslim-408")
            asr_item = {"title": h["title"], "main": h["text"], "source": h["source"], "refs": [f"hadith:{h['id']}"]}
        out.append({
            "id": f"{d}-friday-asr", "date": str(d), "slot": "feed_friday_asr", "kind": "feed",
            "time": (t["asr"] + timedelta(minutes=cfg["friday_asr_post_after_min"])).isoformat(),
            "note": None, **asr_item, "caption": captions.friday_salawat(asr_item, cfg, n), "status": "pending",
        })
        dua = duas[fri_n % len(duas)]
        feed = {"title": f"{cfg['deceased_name']} · رحمه الله", "main": dua["main"], "weight": 400,
                "source": dua["source"], "refs": [f"hisn:{dua['hisn_id']}"]}
        cap = captions.dua_deceased(feed, cfg, n)
        slot = "feed_dua_deceased"
    else:
        k = non_friday_index(epoch, d)
        if k >= len(athar):
            return out  # bank exhausted: no repeats — add more athar before extending
        a = athar[k]
        feed = {"title": a["title"], "main": a["text"], "source": a["source"], "weight": 500,
                "refs": [f"zuhd:{a['num']}"]}
        cap = captions.athar(feed, cfg, n)
        slot = "feed_athar"
    out.append({"id": f"{d}-maghrib", "date": str(d), "slot": slot, "kind": "feed",
                "time": t["maghrib"].isoformat(), "note": None, **feed, "caption": cap, "status": "pending"})
    if cfg.get("reels_per_day", 1) > 0:
        import reels_plan
        out += reels_plan.bank_items(d, epoch, cfg, out)
    return out


def build(start: date, days: int):
    cfg = load_cfg()
    athar = yaml.safe_load((ROOT / "data" / "athar.yaml").read_text(encoding="utf-8"))
    hadith = yaml.safe_load((ROOT / "data" / "hadith.yaml").read_text(encoding="utf-8"))
    frames = json.loads((ROOT / "data" / "adhkar_frames.json").read_text(encoding="utf-8"))
    duas = adhkar.dead_duas()
    bank = load_bank()
    epoch = date.fromisoformat(bank.setdefault("epoch", str(start)))
    have = {x["id"] for x in bank["items"]}
    added = 0
    for i in range(days):
        d = start + timedelta(days=i)
        for it in items_for_day(d, epoch, cfg, athar, hadith, duas, frames):
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
