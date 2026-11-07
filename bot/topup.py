"""Content auto top-up (no API calls): keep at least 30 days of content in the bank.
Run weekly by GitHub Actions. New items are built from the same verified sources
(Tanzil, Hisn al-Muslim, al-Zuhd, As-Sa'di) and pass the same tests."""
from datetime import date, datetime, timedelta

import build_bank
from prayer import TZ


def main(min_days=30, chunk=14):
    bank = build_bank.load_bank()
    today = datetime.now(TZ).date()
    last = max((date.fromisoformat(x["date"]) for x in bank["items"]), default=today)
    if (last - today).days >= min_days:
        print(f"bank runs to {last} — no top-up needed")
        return 0
    added, total = build_bank.build(last + timedelta(days=1), chunk)
    print(f"topped up {added} items ({last + timedelta(days=1)} +{chunk}d), total {total}")
    return added


if __name__ == "__main__":
    main()
