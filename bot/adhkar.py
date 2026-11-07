"""Adhkar from Hisn al-Muslim (data/hisn/*.json, source: hisnmuslim.com API).

Text is used verbatim except for presentation cleanup:
- strip the (( )) quote marks and the bracketed "[وإذا أمسى قال ...]" notes,
- move a trailing count note like "(ثلاثَ مرَّاتٍ)" to its own line,
- Quranic passages are replaced by the Tanzil text (see QURAN_ITEMS) so the Quran
  always comes from the Uthmani file.
Items whose wording is only for the morning are never used in the evening.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from quran import title_for, verse

HISN = Path(__file__).resolve().parents[1] / "data" / "hisn"

# Hisn item ID -> list of (sura, start, end), rendered from Tanzil instead of the hisn text.
QURAN_ITEMS = {
    75: [(2, 255, 255)],                                   # Ayat al-Kursi
    76: [(112, 1, 4), (113, 1, 5), (114, 1, 6)],           # al-Mu'awwidhat (x3)
    100: [(2, 255, 255)],
    101: [(2, 285, 286)],
}
COUNT_FROM_HISN = {76: "ثلاثَ مرَّاتٍ"}  # count stated in the hisn text for these Quran items

MORNING_ONLY = {77, 78, 80, 81, 89, 90, 93, 94, 95}   # wording says أصبح / "إذا أصبح"
EVENING_ONLY = {97}                                   # "إذا أمسى"
SKIP = {99, 110, 106}  # instructions/actions rather than a recitable text, or nested counts


def _load(chapter: int):
    data = json.loads((HISN / f"{chapter}.json").read_text(encoding="utf-8-sig"))
    return list(data.values())[0]


def _clean(text: str):
    """Split '((dhikr)) (note)' into the dhikr and the book's own count note, verbatim."""
    t = re.sub(r"\[[^\]]*\]", "", text)          # remove bracketed evening/variant notes
    count = None
    if "((" in t and "))" in t:
        main = t[t.find("((") + 2: t.rfind("))")]
        note = t[t.rfind("))") + 2:]
        note = re.sub(r"[()]", "", note)
        note = re.sub(r"\s+", " ", note).strip(" .،,")
        count = note or None
    else:
        main = t
    main = main.replace("ـــ", "")
    main = re.sub(r"\s+", " ", main).strip(" .")
    main = re.sub(r"\s+،", "،", main)
    return main, count


@lru_cache
def items(session: str):
    """session: 'morning' | 'evening' | 'sleep' -> list of dicts {hisn_id, main, count, source}"""
    chapter = 28 if session == "sleep" else 27
    out = []
    for it in _load(chapter):
        i = it["ID"]
        if i in SKIP:
            continue
        if session == "evening" and i in MORNING_ONLY:
            continue
        if session == "morning" and i in EVENING_ONLY:
            continue
        if i in QURAN_ITEMS:
            # one frame per sura (like the account's own slides), same count note on each
            for s, a, b in QURAN_ITEMS[i]:
                t, src = verse(s, a, b, basmala=False)
                out.append({"hisn_id": i, "main": t, "count": fmt_count(COUNT_FROM_HISN.get(i), 1),
                            "source": src, "title": title_for(s, a, b)})
            continue
        main, note = _clean(it["ARABIC_TEXT"])
        out.append({"hisn_id": i, "main": split_lines(main), "count": fmt_count(note, it["REPEAT"]),
                    "source": "حصن المسلم", "title": short_title(main)})
    return out


TASHKEEL = re.compile(r"[ً-ٰٟـ]")
NUM_WORDS = {"ثلاث": 3, "أربع": 4, "اربع": 4, "سبع": 7, "عشر": 10, "مائة": 100, "مائه": 100, "مئة": 100}


def _plain(s):
    return TASHKEEL.sub("", s)


def fmt_count(note, repeat):
    """'ثلاثَ مرَّاتٍ إذا أصبحَ' -> '٣ مرات · إذا أصبح' ; None/1 -> 'مرة واحدة'."""
    from quran import ar_num
    if not note:
        return "مرة واحدة" if repeat in (None, 1) else f"{ar_num(repeat)} مرات"
    p = _plain(note)
    if "أو" in p:          # e.g. "عشر مرات، أو مرة واحدة عند الكسل" — keep the book's words
        return p
    for w, n in NUM_WORDS.items():
        if p.startswith(w):
            rest = re.sub(r"^\S+\s+(مرات|مرة)\s*", "", p).strip()
            base = f"{ar_num(n)} {'مرات' if n <= 10 else 'مرة'}"
            return f"{base} · {rest}" if rest else base
    return p


def split_lines(text, target=28):
    """Clause-per-line like the account's slides (break after ، . :), merging very short
    neighbouring clauses so long duas don't become a thin column."""
    t = re.sub(r"\s*([،.:])\s*", r"\1\n", text)
    clauses = [ln.strip(" ،.:") for ln in t.split("\n") if ln.strip(" ،.:")]
    lines, cur = [], ""
    for c in clauses:
        if cur and len(_plain(cur)) + len(_plain(c)) + 1 <= target:
            cur = f"{cur}، {c}"
        else:
            if cur:
                lines.append(cur)
            cur = c
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def short_title(text, max_words=5):
    first = re.split(r"[،.:]", text)[0].strip()
    words = first.split()
    return " ".join(words[:max_words]) if len(words) <= max_words else " ".join(words[:3])


def dead_duas():
    """Duas for the deceased (male), from 'الدعاء للميت في الصلاة عليه' and 'بعد الدفن'."""
    keep = {156, 159, 164}
    out = []
    for ch in (55, 59):
        for it in _load(ch):
            if it["ID"] in keep:
                main, _ = _clean(it["ARABIC_TEXT"])
                out.append({"hisn_id": it["ID"], "main": split_lines(main), "source": "حصن المسلم"})
    return out


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for s in ("morning", "evening", "sleep"):
        print(s, len(items(s)))
    print(items("morning")[2])
    print(dead_duas()[0])
