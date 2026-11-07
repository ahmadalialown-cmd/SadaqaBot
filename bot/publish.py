"""Publish whatever is due. Run every 30 min by GitHub Actions (once enabled).

- Only items with status "approved" (or everything if auto_approve) are published.
- Never double-posts: state/posted.json records every published id.
- Failures are recorded and retried on the next run (until max_late_minutes passes).
- --dry-run: renders and logs what would be published; no Instagram calls.
- --only ID: publish exactly this item now (used for the one-off test story).
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
import yaml

from prayer import TZ

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "media"
STATE = ROOT / "state" / "posted.json"


def load_json(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def repo_slug():
    slug = os.environ.get("GITHUB_REPOSITORY")
    if slug:
        return slug
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True,
                         cwd=ROOT).stdout.strip()
    return url.split("github.com/")[-1].removesuffix(".git")


def public_url(rel: str):
    return f"https://raw.githubusercontent.com/{repo_slug()}/main/{rel}"


def ensure_media(items, push: bool):
    """Render missing images into media/, commit+push them so they get a public URL."""
    from render import render
    missing = [x for x in items if x["kind"] != "reel" and not x.get("image")
               and not (MEDIA / f"{x['id']}.png").exists()]
    if missing:
        render(missing, MEDIA)
    if missing and push:
        subprocess.run(["git", "add", "media"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"media: {len(missing)} image(s)"], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)
    for x in items:
        rel = x.get("video") or x.get("image") or f"media/{x['id']}.png"
        url = public_url(rel)
        for _ in range(24):  # wait for raw.githubusercontent.com to serve it
            if requests.head(url, timeout=20).status_code == 200:
                break
            time.sleep(5)
        x["_url"] = url


def due_items(bank, state, cfg, now, only=None):
    out = []
    for x in bank["items"]:
        if only:
            if x["id"] == only:
                out.append(x)
            continue
        if x["id"] in state["posted"]:
            continue
        if not (cfg.get("auto_approve") or x["status"] == "approved"):
            continue
        t = datetime.fromisoformat(x["time"])
        if t <= now <= t + timedelta(minutes=cfg["max_late_minutes"]):
            out.append(x)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--now", help="pretend time (ISO), for testing")
    a = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    if cfg.get("paused") and not a.dry_run and not a.only:
        print("paused: true in config.yaml — nothing published.")
        return 0
    bank = load_json(ROOT / "data" / "bank.json", {"items": []})
    state = load_json(STATE, {"posted": {}, "failed": {}, "warning": None})
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(TZ)
    due = due_items(bank, state, cfg, now, a.only)
    print(f"{now:%Y-%m-%d %H:%M} — due: {len(due)}")
    if not due:
        return 0

    if a.dry_run:
        from render import render
        out = ROOT / "out" / "dry_run"
        render([x for x in due if x["kind"] != "reel"], out)
        for x in due:
            print(f"  DRY {x['time'][11:16]} {x['kind']:5s} {x['id']} — {x['title']} | {x['source']}")
        print(f"  images in {out}")
        return 0

    import graph
    ok, warn = graph.token_status()
    state["warning"] = warn
    if warn:
        print(warn)
    if not ok:
        save_json(STATE, state)
        print("token invalid — stopping")
        return 1
    who = graph.username()
    if who != cfg["instagram_username"]:
        print(f"account mismatch: token is for @{who}, config wants @{cfg['instagram_username']} — stopping")
        return 1

    ensure_media(due, push=bool(os.environ.get("GITHUB_ACTIONS")))
    errors = 0
    try:
        used, total = graph.publishing_quota()
        print(f"publishing quota: {used}/{total} in the last 24h")
    except Exception:
        used, total = 0, 10**9
    # feed posts first so a tight quota never drops them in favour of story frames
    due.sort(key=lambda x: (x["kind"] == "story", x["time"], x["id"]))
    for x in due:
        if x["id"] in state["posted"]:
            continue  # never double-post
        if used >= total:
            state["warning"] = f"وصلنا حد النشر اليومي في انستقرام ({used}/{total}) — الباقي ينتظر."
            print(state["warning"])
            break
        try:
            kind = x["kind"]
            mid = graph.publish(
                image_url=None if kind == "reel" else x["_url"],
                video_url=x["_url"] if kind == "reel" else None,
                caption=x.get("caption", ""), kind=kind)
            state["posted"][x["id"]] = {"media_id": mid, "at": datetime.now(TZ).isoformat()}
            used += 1
            state["failed"].pop(x["id"], None)
            print(f"  ✔ {x['id']} -> {mid}")
        except Exception as e:  # retried next run
            errors += 1
            f = state["failed"].setdefault(x["id"], {"attempts": 0})
            f["attempts"] += 1
            f["error"] = str(e)[:300]
            print(f"  ✖ {x['id']}: {f['error']}")
        save_json(STATE, state)
    return 1 if errors == len(due) else 0  # fail the run only if nothing went out


if __name__ == "__main__":
    sys.exit(main())
