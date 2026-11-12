"""Warm-up ramp after the account locks (no input needed).

From config `warmup.start_date`:
  week 1  (days 0-6):  1 publish/day  — the Maghrib feed post only
  week 2  (days 7-13): 2 publishes/day — Maghrib feed + the daily reel
  day 14+:             full schedule (feed, reel, Friday posts, adhkar stories)
Always: spacing between publishes, a per-run cap, and a hard daily cap well under the
API limit (100/24h). Items the ramp doesn't allow are skipped (not posted late).
"""
from datetime import date, datetime

FEED_SLOTS = ("feed_athar", "feed_dua_deceased", "feed_verse", "feed_hadith")


def stage(cfg, today: date):
    w = cfg.get("warmup") or {}
    start = date.fromisoformat(str(w.get("start_date", "2000-01-01")))
    if today < start:
        return None, (start - today).days
    d = (today - start).days
    return (1 if d < 7 else 2 if d < 14 else 3), d


def allowed(item, st):
    if st == 3:
        return True
    if item["id"].endswith("-maghrib") and item["slot"] in FEED_SLOTS:
        return True
    if st == 2 and item["id"].endswith("-reel-1"):
        return True
    return False


# Calm mode (config `calm: true`, set 2026-11-12): ONE publish per slot per day, nothing extra:
#   morning adhkar story (after Fajr), evening adhkar story (after Asr), the Maghrib feed post
#   (athar; Friday = dua for the deceased), sleep adhkar story (22:00), Friday Asr post.
# Adhkar = the first frame of the account's own carousel (one story, no bursts). No reels.
CALM_SUFFIXES = ("-morning-01", "-evening-01", "-sleep-01", "-maghrib", "-friday-asr")


def calm_allowed(item):
    return item["kind"] != "reel" and item["id"].endswith(CALM_SUFFIXES)


def daily_cap(cfg, st):
    if cfg.get("calm"):
        return int(cfg.get("calm_max_per_day", 5))
    w = cfg.get("warmup") or {}
    return {1: 1, 2: 2}.get(st, int(w.get("max_per_day", 60)))


def published_today(state, today: date):
    n = 0
    for v in state["posted"].values():
        try:
            if datetime.fromisoformat(v["at"]).date() == today:
                n += 1
        except Exception:
            pass
    return n
