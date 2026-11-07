"""Quran lookup from the local Tanzil texts (never from memory).

Two Tanzil scripts are kept in data/:
- quran-simple.txt  (imla'i script with full tashkeel and pause marks) — used for display,
  matching the account's existing posts;
- quran-uthmani.txt (Uthmani script) — kept for reference/alternative style.
"""
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
FILES = {"simple": "quran-simple.txt", "uthmani": "quran-uthmani.txt"}
BASMALA = {"simple": "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ",
           "uthmani": "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ"}
NAME_FIX = {14: "إبراهيم"}  # Tanzil metadata spells it without hamza
PAUSE_MARKS = "ۖۗۚۛۙۘ"     # Quranic pause (waqf) marks
SPECIAL_TITLES = {(2, 255, 255): "آية الكرسي"}


@lru_cache
def _verses(script="simple"):
    v = {}
    for line in (DATA / FILES[script]).read_text(encoding="utf-8").splitlines():
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


def sura_name(sura: int) -> str:
    return NAME_FIX.get(sura, _suras()[sura][0])


def _lines(text: str):
    """Break an ayah into display lines at its pause marks (marks themselves dropped).
    The ۞ hizb/rub' marker is a section sign, not part of the ayah, so it's removed."""
    text = text.replace("۞", "").strip()
    parts = re.split(f"\\s*[{PAUSE_MARKS}]\\s*", text)
    return [p.strip() for p in parts if p.strip()]


def verse(sura: int, start: int, end: int | None = None, script="simple", numbers=False,
          basmala=True):
    """Return (text, source_line). One ayah per line, long ayat split at pause marks.
    basmala=False drops the basmala Tanzil prefixes to ayah 1 (the account's adhkar
    slides don't show it). Raises KeyError on an invalid reference."""
    end = end or start
    name, count = _suras()[sura]
    name = NAME_FIX.get(sura, name)
    if not (1 <= start <= end <= count):
        raise KeyError(f"{sura}:{start}-{end} out of range (1..{count})")
    out = []
    bas = _verses(script)[(1, 1)]  # exact basmala string as written in this Tanzil file
    for a in range(start, end + 1):
        t = _verses(script)[(sura, a)]
        # Tanzil prefixes the basmala to ayah 1 (except Al-Fatiha, where it IS ayah 1)
        if a == 1 and sura != 1 and t.startswith(bas):
            t = t[len(bas):].strip()
            if basmala:
                out.append(bas)
        ls = _lines(t)
        if numbers:
            ls[-1] += f" ﴿{ar_num(a)}﴾"
        out.extend(ls)
    ref = ar_num(start) if start == end else f"{ar_num(start)}–{ar_num(end)}"
    return "\n".join(out), f"سورة {name} {ref}"


def title_for(sura, start, end=None):
    end = end or start
    if (sura, start, end) in SPECIAL_TITLES:
        return SPECIAL_TITLES[(sura, start, end)]
    _, count = _suras()[sura]
    return f"سورة {sura_name(sura)}"


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    s, a = map(int, sys.argv[1].split(":"))
    t, src = verse(s, a)
    print(t)
    print(src)
