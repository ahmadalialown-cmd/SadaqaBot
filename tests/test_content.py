"""Content safety checks. Run: python -m pytest -q tests  (or python tests/test_content.py)"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))

from prayer import times  # noqa: E402
from quran import verse, _verses  # noqa: E402

BANK = json.loads((ROOT / "data" / "bank.json").read_text(encoding="utf-8"))["items"]


def test_quran_text_complete():
    assert len(_verses()) == 6236


def test_bank_quran_matches_tanzil():
    """Every Quran item's text must be exactly what the Tanzil file gives for its ref."""
    for x in BANK:
        for r in x.get("refs", []):
            if r.startswith("quran:") and x["slot"] != "reel":
                s, rng = r.split(":")[1], r.split(":")[2]
                a, b = rng.split("-") if "-" in rng else (rng, rng)
                txt, src = verse(int(s), int(a), int(b))
                if len(x["refs"]) == 1 and x["source"].startswith("سورة"):
                    assert x["main"] == txt, x["id"]
                    assert x["source"] == src, x["id"]


def test_every_item_has_source_and_pending_or_approved():
    for x in BANK:
        assert x.get("source"), x["id"]
        assert x["status"] in ("pending", "approved", "rejected"), x["id"]


def test_unique_ids():
    ids = [x["id"] for x in BANK]
    assert len(ids) == len(set(ids))


def test_feed_has_caption():
    for x in BANK:
        if x["kind"] == "feed":
            assert x["caption"].strip(), x["id"]


def test_athar_exact_from_book():
    """Every athar text must be the book's matn (only isnad + digital markers removed)."""
    import yaml
    import zuhd
    from build_athar import clean
    athar = yaml.safe_load((ROOT / "data" / "athar.yaml").read_text(encoding="utf-8"))
    nums = [a["num"] for a in athar]
    assert len(nums) == len(set(nums))
    for a in athar:
        sp, raw = zuhd.extract(a["num"])
        assert raw == a["raw"] and raw in zuhd.narrations()[a["num"]]["text"], a["num"]
        assert a["text"] == clean(raw), a["num"]
        assert "صلى الله عليه وسلم" not in zuhd.narrations()[a["num"]]["text"], a["num"]


def test_bank_athar_no_repeats_and_match():
    import yaml
    athar = {a["num"]: a for a in yaml.safe_load((ROOT / "data" / "athar.yaml").read_text(encoding="utf-8"))}
    used = [x["refs"][0] for x in BANK if x["slot"] == "feed_athar"]
    assert len(used) == len(set(used))
    for x in BANK:
        if x["slot"] == "feed_athar":
            a = athar[int(x["refs"][0].split(":")[1])]
            assert x["main"] == a["text"] and x["source"] == a["source"], x["id"]


def test_adhkar_story_frames_exist():
    for x in BANK:
        if x.get("image"):
            assert (ROOT / x["image"]).exists(), x["id"]


def test_prayer_times_doha_2026_11_06():
    t = times(date(2026, 11, 6))
    # Qatar (Awqaf) method values from timesprayer.com for that day
    assert f"{t['fajr']:%H:%M}" == "04:27"
    assert f"{t['asr']:%H:%M}" == "14:27"
    assert f"{t['maghrib']:%H:%M}" == "16:51"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
