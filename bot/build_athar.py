"""Build data/athar.yaml: the curated athar from كتاب الزهد للإمام أحمد used for the
daily feed post. Each matn is extracted from data/zuhd/zuhd.md and is an exact
substring of its narration (only the isnad is dropped). Presentation cleanup only
removes the digital edition's markers: manuscript tags (ms123) and page tags ([ص: 12])."""
import re
from pathlib import Path

import yaml

import zuhd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "athar.yaml"

RA = "رضي الله عنه"
RH = "رحمه الله"
# narration number -> (speaker as displayed, honorific). Speakers verified against each isnad.
PICKS = {
    103: ("سعيد بن جبير", RH), 178: ("أُبيّ بن كعب", RA), 574: ("أبو بكر الصديق", RA),
    586: ("معاوية بن أبي سفيان", RA),
    1313: ("خليد العصري", RH), 1317: ("خليد العصري", RH),
    1323: ("مطرف بن عبد الله", RH), 1325: ("مطرف بن عبد الله", RH), 1342: ("مطرف بن عبد الله", RH),
    1344: ("مطرف بن عبد الله", RH), 1348: ("مطرف بن عبد الله", RH),
    1394: ("مسلم بن يسار", RH), 1403: ("مسلم بن يسار", RH),
    **{n: ("الحسن البصري", RH) for n in (1448, 1480, 1483, 1497, 1514, 1521, 1524, 1527, 1528, 1547,
                                          1548, 1559, 1561, 1581, 1586, 1595, 1619, 1625, 1630, 1632,
                                          1634, 1636, 1637, 1644, 1646, 1656, 201)},
    1672: ("معاوية بن قرة", RH),
    1682: ("عمر بن عبد العزيز", RH), 1708: ("عمر بن عبد العزيز", RH), 1737: ("عمر بن عبد العزيز", RH),
    1743: ("أبو العالية", RH), 1754: ("بكر بن عبد الله المزني", RH), 1828: ("بكر بن عبد الله المزني", RH),
    1756: ("مورق العجلي", RH), 1761: ("مورق العجلي", RH), 1768: ("محمد بن سيرين", RH),
    1823: ("محمد بن واسع", RH),
    **{n: ("مالك بن دينار", RH) for n in (1864, 1870, 1872, 1884, 1886)},
    1917: ("حسان بن أبي سنان", RH), 1920: ("أبو المنهال", RH),
    1963: ("الربيع بن خثيم", RH), 1985: ("الربيع بن خثيم", RH),
    **{n: ("مسروق", RH) for n in (2029, 2033, 2038, 2040, 2042)},
    2048: ("عمرو بن ميمون", RH), 2071: ("إبراهيم التيمي", RH), 2090: ("أبو البختري الطائي", RH),
    2092: ("الحارث بن قيس الجعفي", RH), 2142: ("يزيد بن معاوية النخعي", RH), 2168: ("سعيد بن جبير", RH),
    2176: ("وهب بن منبه", RH), 2178: ("وهب بن منبه", RH), 2191: ("وهب بن منبه", RH),
    2218: ("مجاهد", RH), 2233: ("أبو زرعة بن عمرو بن جرير", RH), 2237: ("أبو إدريس الخولاني", RH),
    2240: ("إبراهيم بن أدهم", RH), 2264: ("خالد بن معدان", RH),
    **{n: ("بلال بن سعد", RH) for n in (2267, 2268, 2271, 2273)},
    2283: ("مكحول", RH), 2309: ("رجاء بن حيوة", RH),
}


def clean(s):
    s = re.sub(r"\s*ms\d+\s*", " ", s)
    s = re.sub(r"\s*\[ص: ?\d+\]\s*", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def interleave(items):
    """Order so the same speaker doesn't appear on consecutive days."""
    by = {}
    for it in items:
        by.setdefault(it["speaker"], []).append(it)
    queues = sorted(by.values(), key=len, reverse=True)
    out, last = [], None
    while any(queues):
        queues.sort(key=len, reverse=True)
        for q in queues:
            if q and q[0]["speaker"] != last:
                out.append(q.pop(0))
                last = out[-1]["speaker"]
                break
        else:
            q = next(q for q in queues if q)
            out.append(q.pop(0))
            last = out[-1]["speaker"]
    return out


def main():
    items = []
    for n, (speaker, hon) in sorted(PICKS.items()):
        sp, raw = zuhd.extract(n)
        assert raw in zuhd.narrations()[n]["text"]
        items.append({"num": n, "speaker": speaker, "title": f"قال {speaker} {hon}",
                      "text": clean(raw), "raw": raw, "source": zuhd.source_line(n)})
    items = interleave(items)
    OUT.write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=1000), encoding="utf-8")
    print(f"{len(items)} athar -> {OUT}")


if __name__ == "__main__":
    main()
