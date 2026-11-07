"""Build review/review.html for the next N days: image, caption, time, sources, status."""
import argparse
import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from prayer import TZ
from render import render

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review"

SLOT_AR = {
    "story_morning": "ستوري · أذكار الصباح", "story_evening": "ستوري · أذكار المساء",
    "story_sleep": "ستوري · أذكار النوم", "feed_verse": "بوست · آية (المغرب)",
    "feed_hadith": "بوست · حديث (المغرب)", "feed_dua_deceased": "بوست · دعاء لسعود (المغرب)",
    "feed_friday_asr": "بوست · عصر الجمعة", "reel": "ريلز",
}
DAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def build(start: date, days: int):
    bank = json.loads((ROOT / "data" / "bank.json").read_text(encoding="utf-8"))["items"]
    end = start + timedelta(days=days - 1)
    sel = [x for x in bank if start <= date.fromisoformat(x["date"]) <= end and x["status"] != "rejected"]
    render([x for x in sel if x["kind"] != "reel"], OUT / "img")
    esc = html.escape
    rows, cur = [], None
    for x in sel:
        if x["date"] != cur:
            cur = x["date"]
            d = date.fromisoformat(cur)
            rows.append(f'<h2>{DAYS_AR[d.weekday()]} {cur}</h2>')
        t = x["time"][11:16]
        cap = esc(x.get("caption") or "—").replace("\n", "<br>")
        refs = esc(", ".join(x.get("refs", [])))
        rows.append(f"""<div class="card {x['status']}"><img loading="lazy" src="img/{esc(x['id'])}.png">
<div class="meta"><b>{t}</b> · {SLOT_AR.get(x['slot'], x['slot'])} · <span class="st">{x['status']}</span>
<div class="id">{esc(x['id'])}</div><div class="src">المصدر: {esc(x.get('source') or '')} {('· ' + esc(x['note'])) if x.get('note') else ''}</div>
<div class="refs">{refs}</div><div class="cap">{cap}</div></div></div>""")
    page = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>مراجعة المحتوى</title>
<style>
:root{{--bg:#f6f2ec;--fg:#2b2622;--card:#fff;--muted:#7a6f66;--accent:#6E6459}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1d1a17;--fg:#eee6db;--card:#2a2622;--muted:#b3a89c}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font-family:Tahoma,sans-serif}}
h1{{font-size:22px}} h2{{margin:28px 0 10px;border-bottom:1px solid var(--muted);padding-bottom:6px}}
.card{{display:flex;gap:14px;background:var(--card);border-radius:12px;padding:12px;margin:10px 0;flex-wrap:wrap}}
.card img{{width:180px;max-width:100%;border-radius:8px}}
.meta{{flex:1;min-width:220px;font-size:14px;line-height:1.7}}
.id,.refs{{color:var(--muted);font-size:12px;direction:ltr;text-align:right}}
.cap{{margin-top:6px;white-space:normal}} .approved .st{{color:#2e7d32}} .pending .st{{color:#b26a00}}
.note{{background:var(--card);padding:12px;border-radius:12px;line-height:1.8}}
</style></head><body>
<h1>مراجعة المحتوى: {start} ← {end}</h1>
<div class="note">راجع كل صورة ونصها ومصدرها. الآيات من نص المصحف (Tanzil)، والأذكار من حصن المسلم، والأحاديث من الصحيحين.
<b>المحتوى الديني يحتاج مراجعة من مختص قبل النشر.</b><br>
للموافقة: قل لـ Claude «اعتمد الأسبوع» أو اكتب أرقام العناصر اللي تبي تعدّلها.</div>
{''.join(rows)}
</body></html>"""
    OUT.mkdir(exist_ok=True)
    (OUT / "review.html").write_text(page, encoding="utf-8")
    return OUT / "review.html", len(sel)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=str(datetime.now(TZ).date() + timedelta(days=1)))
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    p, n = build(date.fromisoformat(a.start), a.days)
    print(f"{n} items -> {p}")
