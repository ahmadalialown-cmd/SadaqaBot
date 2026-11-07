"""Approve / reject bank items, then pre-render approved images into media/.

  python bot/approve.py --days 7              approve everything pending in the next 7 days
  python bot/approve.py --through 2026-11-14  approve pending items up to that date
  python bot/approve.py --ids ID [ID ...]     approve specific items
  python bot/approve.py --reject ID [ID ...]  reject items (never published)
  python bot/approve.py --status              show counts per status
"""
import argparse
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from prayer import TZ

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data" / "bank.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int)
    ap.add_argument("--through")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--reject", nargs="*")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    items = bank["items"]
    if a.status:
        print(Counter(x["status"] for x in items))
        return
    today = datetime.now(TZ).date()
    until = (date.fromisoformat(a.through) if a.through else
             today + timedelta(days=a.days) if a.days else None)
    changed = []
    for x in items:
        if a.reject and x["id"] in a.reject:
            x["status"] = "rejected"
            continue
        pick = (a.ids and x["id"] in a.ids) or (until and date.fromisoformat(x["date"]) <= until)
        if pick and x["status"] == "pending":
            x["status"] = "approved"
            changed.append(x)
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"approved {len(changed)}; rejected {len(a.reject or [])}")
    if changed and not a.no_render:
        from render import render
        render(changed, ROOT / "media")
        print("rendered into media/ — commit and push to make them live")


if __name__ == "__main__":
    main()
