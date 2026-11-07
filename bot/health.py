"""Self-healing state + notifications.

state/health.json:
  {"auto_paused": null | {"kind": auth|rate_limit|blocked|permission|other,
                          "reason": str, "since": iso, "retry_after": iso},
   "last_probe": iso | null}

Policy (never hammer):
  rate_limit -> pause 24h, then resume automatically at the ramp's current level
  blocked    -> pause 72h (Meta flagged an action), then one probe, resume if OK
  auth/permission -> pause; probe the token at most once per 24h; resume when valid
  other (3 failures in a row) -> pause 6h
Notifications are GitHub issues in the repo (GitHub emails the owner) — no extra secrets.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

from prayer import TZ

ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / "state" / "health.json"
BACKOFF_H = {"rate_limit": 24, "blocked": 72, "auth": 24, "permission": 24, "other": 6}


def load():
    if HEALTH.exists():
        return json.loads(HEALTH.read_text(encoding="utf-8"))
    return {"auto_paused": None, "last_probe": None, "consecutive_other": 0}


def save(h):
    HEALTH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")


def now():
    return datetime.now(TZ)


def pause(h, kind, reason):
    t = now()
    h["auto_paused"] = {"kind": kind, "reason": reason[:300], "since": t.isoformat(),
                        "retry_after": (t + timedelta(hours=BACKOFF_H.get(kind, 24))).isoformat()}
    save(h)
    notify(f"⏸️ SadaqaBot أوقف النشر تلقائياً ({kind})",
           f"السبب: {reason[:300]}\n\nبيحاول يرجع لحاله بعد {BACKOFF_H.get(kind, 24)} ساعة "
           f"(فحص واحد بس، بدون إلحاح).\n"
           + ("إذا كان السبب التوكن: شغّل setup_secrets.ps1 (شوف README_AR.md).\n" if kind in ("auth", "permission") else "")
           + "لإيقاف كل شي يدوياً: paused: true في config.yaml.")


def resume(h, note=""):
    was = h.get("auto_paused")
    h["auto_paused"] = None
    h["consecutive_other"] = 0
    save(h)
    if was:
        notify("▶️ SadaqaBot رجع ينشر", f"رجع النشر بعد إيقاف تلقائي ({was['kind']}). {note}")


def may_probe(h):
    """True if a paused system is allowed to make ONE API call now."""
    ap = h.get("auto_paused")
    if not ap:
        return True
    if now() < datetime.fromisoformat(ap["retry_after"]):
        return False
    last = h.get("last_probe")
    return not last or now() - datetime.fromisoformat(last) > timedelta(hours=23)


def notify(title, body):
    """Open a GitHub issue (emails the repo owner). Silent no-op outside Actions."""
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    print(f"[notify] {title}")
    if not (token and repo):
        return
    try:
        requests.post(f"https://api.github.com/repos/{repo}/issues", timeout=30,
                      headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                      json={"title": title, "body": body})
    except Exception as e:  # notifications must never break publishing
        print(f"[notify] failed: {e}")
