"""Quran lookup from the local Tanzil Uthmani text (never from memory)."""
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


@lru_cache
def _verses():
    v = {}
    for line in (DATA / "quran-uthmani.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3 and parts[0].isdigit():
            v[(int(parts[0]), int(parts[1]))] = parts[2].strip()
    assert len(v) == 6236, f"Quran text incomplete: {len(v)} verses"
    return v


@lru_cache
def _suras():
    root = ET.parse(DATA / "quran-data.xml").getroot()
    return {int(s.get("index")): (s.get("name"), int(s.get("ayas"))) for s in root.iter("sura")}


def ar_num(n) -> str:
    return str(n).translate(AR_DIGITS)


def verse(sura: int, start: int, end: int | None = None):
    """Return (text, source_line). Raises KeyError on an invalid reference."""
    end = end or start
    name, count = _suras()[sura]
    if not (1 <= start <= end <= count):
        raise KeyError(f"{sura}:{start}-{end} out of range (1..{count})")
    parts = [f"{_verses()[(sura, a)]} ﴿{ar_num(a)}﴾" for a in range(start, end + 1)]
    ref = ar_num(start) if start == end else f"{ar_num(start)}–{ar_num(end)}"
    return " ".join(parts), f"سورة {name} {ref}"


if __name__ == "__main__":
    import sys
    s, a = map(int, sys.argv[1].split(":"))
    t, src = verse(s, a)
    print(t)
    print(src)
