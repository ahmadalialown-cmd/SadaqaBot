"""Weekly optimisation loop (Fridays after Jumu'ah).

- Pulls insights for everything published in the last 7 days (Instagram; Facebook /
  Threads / YouTube when enabled), followers, and new comments (listed, never auto-replied).
- Writes report_AR.md + reports/chart_<date>.png (sends-per-reach by theme).
- Re-weights next week (data/optimizer.json):
    * theme_order: themes ranked by sends/reach → Thursday share-dua rotation + 2nd reel
    * reel_time: the best performing reel hour among the candidates
  and reports exactly what changed.
- Reminds to enable Trial Reels once followers >= 200.
Missing permissions degrade gracefully (the report says what's missing)."""
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import envload
import graph
from prayer import TZ

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "posted.json"
OPT = ROOT / "data" / "optimizer.json"
REPORT = ROOT / "report_AR.md"
FONT = ROOT / "fonts" / "NotoNaskhArabic.ttf"
METRICS = ["reach", "shares", "saved", "likes", "comments", "total_interactions", "views",
           "ig_reels_avg_watch_time", "follows"]
REEL_TIMES = ["13:00", "17:30", "20:30", "21:30"]
THEME_AR = {"athar": "أثر اليوم", "verse": "آية وتفسير", "dua_deceased": "دعاء للميت",
            "dua_sick": "دعاء للمريض", "dua_parents": "دعاء للوالدين", "friday": "الجمعة", None: "أخرى"}


def chart(rows, path):
    """Simple horizontal bar chart (PIL; Arabic shaped by the font where supported)."""
    W, H, pad = 900, 60 + 50 * max(1, len(rows)), 20
    im = Image.new("RGB", (W, H), "#F6F2EC")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(FONT), 22)
    top = max([r[1] for r in rows] + [1e-9])
    d.text((pad, 15), "sends per 1k reach by theme", fill="#2b2622", font=f)
    for i, (label, v) in enumerate(rows):
        y = 60 + i * 50
        w = int((W - 320) * v / top)
        d.rectangle([260, y, 260 + w, y + 30], fill="#6E6459")
        d.text((pad, y), label, fill="#2b2622", font=f)
        d.text((270 + w, y), f"{v:.1f}", fill="#2b2622", font=f)
    im.save(path)


def main():
    envload.load()
    now = datetime.now(TZ)
    since = now - timedelta(days=7)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"posted": {}}
    scopes = graph.token_scopes()
    missing = [s for s in ("instagram_manage_insights", "instagram_manage_comments", "pages_manage_posts")
               if s not in scopes]
    acct = graph.account_info()
    week = {k: v for k, v in state["posted"].items() if datetime.fromisoformat(v["at"]) >= since}

    per_theme = defaultdict(lambda: {"reach": 0, "shares": 0, "saved": 0, "n": 0})
    per_hour = defaultdict(lambda: {"reach": 0, "shares": 0, "n": 0})
    comments, rows = [], []
    for pid, p in week.items():
        if "story" in (p.get("slot") or ""):
            continue  # stories expire; their insights are only available for 24h
        m = graph.media_insights(p["media_id"], METRICS) if "instagram_manage_insights" in scopes else {}
        theme = p.get("theme") or ("athar" if p.get("slot") == "feed_athar" else p.get("slot"))
        t = per_theme[theme]
        t["n"] += 1
        for k in ("reach", "shares", "saved"):
            t[k] += m.get(k) or 0
        if (p.get("slot") or "").startswith("reel"):
            hh = datetime.fromisoformat(p["at"]).strftime("%H:00")
            per_hour[hh]["reach"] += m.get("reach") or 0
            per_hour[hh]["shares"] += m.get("shares") or 0
            per_hour[hh]["n"] += 1
        if "instagram_manage_comments" in scopes:
            for c in graph.media_comments(p["media_id"]):
                if datetime.fromisoformat(c["timestamp"].replace("+0000", "+00:00")) >= since:
                    comments.append((pid, c))
        rows.append((pid, theme, m))

    spr = {th: (v["shares"] / v["reach"] * 1000 if v["reach"] else 0) for th, v in per_theme.items()}
    ranked = sorted(spr, key=lambda k: -spr[k])
    opt = json.loads(OPT.read_text(encoding="utf-8")) if OPT.exists() else {}
    before = dict(opt)
    changes = []
    if any(per_theme[t]["reach"] for t in per_theme):
        opt["theme_order"] = [t for t in ranked if t]
        if opt.get("theme_order") != before.get("theme_order"):
            changes.append("ترتيب المواضيع: " + " ← ".join(THEME_AR.get(t, t) for t in opt["theme_order"]))
    if per_hour:
        best = max(per_hour, key=lambda h: (per_hour[h]["shares"] / per_hour[h]["reach"]) if per_hour[h]["reach"] else 0)
        cand = min(REEL_TIMES, key=lambda c: abs(int(c[:2]) - int(best[:2])))
        if cand != opt.get("reel_time"):
            opt["reel_time"] = cand
            changes.append(f"وقت الريلز الأساسي صار {cand} (أفضل نسبة إرسال/وصول كانت حول {best})")
    OPT.write_text(json.dumps(opt, ensure_ascii=False, indent=1), encoding="utf-8")

    (ROOT / "reports").mkdir(exist_ok=True)
    chart_path = ROOT / "reports" / f"chart_{now:%Y-%m-%d}.png"
    chart([(str(t), spr[t]) for t in ranked], chart_path)  # Latin keys: PIL can't shape Arabic

    L = [f"# تقرير الأسبوع — {now:%Y-%m-%d}", "",
         f"**المتابعين:** {acct.get('followers_count')} · **عدد المنشورات:** {acct.get('media_count')} · "
         f"**انتشر هالأسبوع:** {len(week)}", ""]
    if (acct.get("followers_count") or 0) >= 200:
        L += ["> 🎉 عديت ٢٠٠ متابع: فعّل **Trial Reels** من تطبيق انستقرام (عند نشر ريلز ← Trial).", ""]
    if missing:
        L += [f"> ⚠️ ناقص صلاحيات للتوكن: {', '.join(missing)} — بعض الأرقام/التعليقات ما انسحبت.", ""]
    L += [f"![chart](reports/{chart_path.name})", "", "## حسب الموضوع", "",
          "| الموضوع | منشورات | الوصول | الإرسال | الحفظ | إرسال/١٠٠٠ وصول |", "|---|---|---|---|---|---|"]
    for t in ranked:
        v = per_theme[t]
        L.append(f"| {THEME_AR.get(t, t)} | {v['n']} | {v['reach']} | {v['shares']} | {v['saved']} | {spr[t]:.1f} |")
    L += ["", "## شنو تغيّر للأسبوع الجاي", ""] + ([f"- {c}" for c in changes] or ["- ما في تغيير (البيانات قليلة)"])
    L += ["", "## تعليقات جديدة (بدون رد تلقائي)", ""]
    L += [f"- @{c.get('username')}: {c.get('text')}" for _, c in comments] or ["- لا يوجد"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:6]))
    print("changes:", changes or "none")


if __name__ == "__main__":
    main()
