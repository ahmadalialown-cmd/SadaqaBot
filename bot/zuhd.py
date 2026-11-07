"""Parse كتاب الزهد للإمام أحمد (data/zuhd/zuhd.md, OpenITI text of Shamela book 8494,
ed. دار الكتب العلمية، بيروت، ط1 1420هـ/1999م) into numbered narrations with page numbers,
and extract (speaker, exact matn) for short non-prophetic athar.

The matn is ALWAYS an exact substring of the narration text (only the isnad is dropped)."""
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "zuhd" / "zuhd.md"
EDITION = "ط. دار الكتب العلمية ١٤٢٠هـ"

HEAD = re.compile(r"^# (\d+) - \s*$")
PAGE = re.compile(r"PageV\d+P(\d+)")
AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


@lru_cache
def narrations():
    """-> {num: {"num", "page", "text"}} ; text = full narration (isnad + matn), whitespace-normalised."""
    lines = SRC.read_text(encoding="utf-8").splitlines()
    out, cur, buf, pending = {}, None, [], []

    def close():
        if cur is not None:
            out[cur] = {"num": cur, "page": None, "text": re.sub(r"\s+", " ", " ".join(buf)).strip()}
            pending.append(cur)

    for ln in lines:
        m = HEAD.match(ln)
        if m:
            close()
            cur, buf = int(m.group(1)), []
            continue
        if cur is None:
            continue
        pm = PAGE.search(ln)
        if pm:
            # page marker closes page N: every narration started since the last marker is on page N
            pg = int(pm.group(1))
            for n in pending:
                out[n]["page"] = out[n]["page"] or pg
            if cur not in out:
                out.setdefault(cur, {"num": cur, "page": pg, "text": ""})
            pending.clear()
            ln = PAGE.sub("", ln)
        t = ln.lstrip("#~ ").strip()
        if t:
            buf.append(t)
    close()
    return out


SPEAKER_RE = re.compile(r"(?:عن|حدثني|حدثنا|سمعت)\s+([^،:«»\"]{3,40}?)\s*،?\s*(?:قال|يقول|أنه قال|كان يقول)\s*:\s*[«\"](.+?)[»\"]\s*$")


def extract(n):
    """-> (speaker, matn) or None. matn is an exact substring of the narration text."""
    t = narrations()[n]["text"]
    m = SPEAKER_RE.search(t)
    if not m:
        return None
    speaker, matn = m.group(1).strip(), m.group(2).strip()
    assert matn in t
    return speaker, matn


def source_line(n):
    # Narration numbers are unique in this edition; page numbers in the digital text are
    # inconsistent (Shamela page tags vs printed [ص:] tags), so cite the number only.
    return f"الزهد للإمام أحمد · رقم {str(n).translate(AR)} · {EDITION}"
