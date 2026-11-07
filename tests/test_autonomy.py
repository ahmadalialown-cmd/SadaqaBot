"""Offline tests for the autonomous layer (no network)."""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

import graph  # noqa: E402
import ramp  # noqa: E402
from prayer import TZ  # noqa: E402

CFG = {"warmup": {"start_date": "2026-11-10", "max_per_day": 60}}


def test_stages():
    assert ramp.stage(CFG, date(2026, 11, 9))[0] is None
    assert ramp.stage(CFG, date(2026, 11, 10))[0] == 1
    assert ramp.stage(CFG, date(2026, 11, 16))[0] == 1
    assert ramp.stage(CFG, date(2026, 11, 17))[0] == 2
    assert ramp.stage(CFG, date(2026, 11, 24))[0] == 3


def test_allowed():
    feed = {"id": "2026-11-10-maghrib", "slot": "feed_athar", "kind": "feed"}
    reel = {"id": "2026-11-10-reel-1", "slot": "reel_athar", "kind": "reel"}
    story = {"id": "2026-11-10-morning-01", "slot": "story_morning", "kind": "story"}
    fri = {"id": "2026-11-13-friday-asr", "slot": "feed_friday_asr", "kind": "feed"}
    assert ramp.allowed(feed, 1) and not ramp.allowed(reel, 1) and not ramp.allowed(story, 1)
    assert not ramp.allowed(fri, 1)
    assert ramp.allowed(reel, 2) and not ramp.allowed(story, 2)
    assert ramp.allowed(story, 3)
    assert ramp.daily_cap(CFG, 1) == 1 and ramp.daily_cap(CFG, 2) == 2


def test_error_kinds():
    assert graph.GraphError("x", 190).kind == "auth"
    assert graph.GraphError("x", 4).kind == "rate_limit"
    assert graph.GraphError("x", 368).kind == "blocked"
    assert graph.GraphError("x", 9, 2207051).kind == "blocked"
    assert graph.GraphError("x", 10).kind == "permission"
    assert graph.GraphError("x", 2).kind == "other"


def test_pick_for_run_stage1_one_per_day():
    import publish
    bank = json.loads((ROOT / "data" / "bank.json").read_text(encoding="utf-8"))
    cfg = {**CFG, "auto_approve": True, "max_late_minutes": 90, "max_late_minutes_stories": 240}
    state = {"posted": {}, "skipped": {}}
    d = date(2026, 11, 11)
    from prayer import times
    now = times(d)["maghrib"] + timedelta(minutes=5)
    due = publish.due_items(bank, state, cfg, now)
    picked = publish.pick_for_run(due, cfg, 1, state, d)
    assert [x["id"] for x in picked] == ["2026-11-11-maghrib"]
    state["posted"]["2026-11-11-maghrib"] = {"at": now.isoformat()}
    assert publish.pick_for_run(publish.due_items(bank, state, cfg, now + timedelta(minutes=30)), cfg, 1, state, d) == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
