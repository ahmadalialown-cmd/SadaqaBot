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
    if push:
        subprocess.run(["git", "add", "media"], cwd=ROOT, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0:
            subprocess.run(["git", "commit", "-m", "media: new file(s)"], cwd=ROOT, check=True)
            subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=ROOT, check=True)
            subprocess.run(["git", "push"], cwd=ROOT, check=True)
    for x in items:
        rel = x.get("video") or x.get("image") or f"media/{x['id']}.png"
        url = public_url(rel)
        for _ in range(24):  # wait for raw.githubusercontent.com to serve it
            if requests.head(url, timeout=20).status_code == 200:
                break
            time.sleep(5)
        x["_url"] = url


def crosspost_facebook(x, cfg, state, graph, st=3):
    """Same approved content to the linked Facebook Page (feed posts + reels). Never blocks IG.
    Only from warm-up stage 3, so the Facebook account isn't hit during the gentle restart."""
    if st < 3 or cfg.get("calm") or not (cfg.get("crosspost") or {}).get("facebook") or x["kind"] not in ("feed", "reel"):
        return
    if x["kind"] == "story":
        return
    try:
        fid = (graph.fb_reel(x["_url"], x.get("caption", "")) if x["kind"] == "reel"
               else graph.fb_photo(x["_url"], x.get("caption", "")))
        state["posted"][x["id"]]["facebook"] = fid
        print(f"    ↳ facebook {fid}")
    except Exception as e:
        state["posted"][x["id"]]["facebook_error"] = str(e)[:200]
        print(f"    ↳ facebook failed: {str(e)[:120]}")


def ensure_reels(items):
    """Render any reel video that isn't there yet (normally done at approval time)."""
    import reels_plan
    for x in items:
        if x["kind"] == "reel" and x.get("reel_spec") and not (ROOT / x["video"]).exists():
            reels_plan.render_reel(x)


def due_items(bank, state, cfg, now, only=None):
    out = []
    skipped = state.setdefault("skipped", {})
    for x in bank["items"]:
        if only:
            if x["id"] == only:
                out.append(x)
            continue
        if x["id"] in state["posted"] or x["id"] in skipped or x["status"] == "rejected":
            continue
        if not (cfg.get("auto_approve") or x["status"] == "approved"):
            continue
        t = datetime.fromisoformat(x["time"])
        # story frames are spread over several runs, so they get a longer window
        late = cfg.get("max_late_minutes_stories", 240) if x["kind"] == "story" else cfg["max_late_minutes"]
        if t <= now <= t + timedelta(minutes=late):
            out.append(x)
    return out


def pick_for_run(due, cfg, st, state, today):
    """Apply the warm-up ramp, the daily cap and the per-run cap."""
    import ramp
    keep = []
    for x in due:
        if (ramp.calm_allowed(x) if cfg.get("calm") else ramp.allowed(x, st)):
            keep.append(x)
        else:
            state["skipped"][x["id"]] = f"ramp stage {st}"
    room = ramp.daily_cap(cfg, st) - ramp.published_today(state, today)
    if room <= 0:
        return []
    keep.sort(key=lambda x: (x["kind"] == "story", x["time"], x["id"]))
    w = cfg.get("warmup") or {}
    feeds = [x for x in keep if x["kind"] != "story"][: int(w.get("per_run_posts", 1))]
    stories = [x for x in keep if x["kind"] == "story"][: int(w.get("per_run_stories", 6))]
    return (feeds + stories)[:room]


def next_in(bank, state, cfg, st, now):
    """Seconds until the next item this mode would publish (-1 if none). Used by the workflow
    to wait for the exact prayer-based time instead of relying on GitHub's cron timing."""
    import ramp
    best = None
    for x in bank["items"]:
        if x["id"] in state["posted"] or x["id"] in state.get("skipped", {}) or x["status"] == "rejected":
            continue
        if not (cfg.get("auto_approve") or x["status"] == "approved"):
            continue
        if not (ramp.calm_allowed(x) if cfg.get("calm") else ramp.allowed(x, st)):
            continue
        t = datetime.fromisoformat(x["time"])
        if t > now and (best is None or t < best):
            best = t
    return int((best - now).total_seconds()) if best else -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--now", help="pretend time (ISO), for testing")
    ap.add_argument("--next-in", action="store_true",
                    help="print seconds until the next publishable item (-1 if none); no API calls")
    a = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    if cfg.get("paused") and not a.dry_run and not a.only:
        print("paused: true in config.yaml — nothing published.")
        return 0
    import health
    import ramp
    bank = load_json(ROOT / "data" / "bank.json", {"items": []})
    state = load_json(STATE, {"posted": {}, "failed": {}, "warning": None})
    state.setdefault("skipped", {})
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(TZ)
    st, info = ramp.stage(cfg, now.date())
    if st is None and not a.only:
        print(f"warm-up starts in {info} day(s) — nothing published, no API calls.")
        return 0
    if a.next_in:
        print(next_in(bank, state, cfg, st, now))
        return 0
    h = health.load()
    due = due_items(bank, state, cfg, now, a.only)
    if not a.only:
        due = pick_for_run(due, cfg, st, state, now.date())
        if not a.dry_run:
            save_json(STATE, state)
    print(f"{now:%Y-%m-%d %H:%M} — ramp stage {st} (day {info}) — to publish this run: {len(due)}")
    if h.get("auto_paused") and not a.dry_run:
        if not health.may_probe(h):
            print(f"auto-paused ({h['auto_paused']['kind']}) until {h['auto_paused']['retry_after']} — no API calls.")
            return 0
    elif not due:
        return 0

    if a.dry_run:
        from render import render
        out = ROOT / "out" / "dry_run"
        render([x for x in due if x["kind"] != "reel"], out)
        for x in due:
            print(f"  DRY {x['time'][11:16]} {x['kind']:5s} {x['id']} — {x['title']} | {x['source']}")
        print(f"  images in {out}")
        return 0

    import envload
    import graph
    envload.load()  # local runs read .env; in Actions the secrets come from env

    # one health check per run (this is also the single "probe" while auto-paused)
    try:
        ok, warn = graph.token_status()
        who = graph.username() if ok else None
    except graph.GraphError as e:
        ok, warn, who = False, None, None
        err = e
    else:
        err = None
    h["last_probe"] = datetime.now(TZ).isoformat()
    state["warning"] = warn
    if warn and "تنتهي" in warn and not state.get("expiry_notified"):
        health.notify("⚠️ SadaqaBot: التوكن قرب ينتهي", warn + "\nشغّل setup_secrets.ps1 (شوف README_AR.md).")
        state["expiry_notified"] = True
    if not ok:
        kind = err.kind if err else "auth"
        if h.get("auto_paused"):
            h["auto_paused"]["retry_after"] = (datetime.now(TZ) + timedelta(hours=24)).isoformat()
            health.save(h)
        else:
            health.pause(h, kind, str(err) if err else "token invalid")
        save_json(STATE, state)
        return 0
    if who != cfg["instagram_username"]:
        health.pause(h, "permission", f"token is for @{who}, config wants @{cfg['instagram_username']}")
        save_json(STATE, state)
        return 0
    if h.get("auto_paused"):
        health.resume(h, "التوكن والحساب سليمين.")
    health.save(h)
    if not due:
        save_json(STATE, state)
        return 0

    ensure_reels(due)
    ensure_media(due, push=bool(os.environ.get("GITHUB_ACTIONS")))
    errors = 0
    try:
        used, total = graph.publishing_quota()
        print(f"publishing quota: {used}/{total} in the last 24h")
    except Exception:
        used, total = 0, 10**9
    total = min(total, int((cfg.get("warmup") or {}).get("api_cap", 60)))  # stay well under the limit
    w = cfg.get("warmup") or {}
    first = True
    for x in due:
        if x["id"] in state["posted"]:
            continue  # never double-post
        if used >= total:
            state["warning"] = f"قريبين من حد النشر ({used}/{total}) — الباقي ينتظر."
            print(state["warning"])
            break
        if not first:  # space publishes out
            time.sleep(int(w.get("gap_story_s", 20)) if x["kind"] == "story" else int(w.get("gap_post_s", 90)))
        first = False
        try:
            kind = x["kind"]
            mid = graph.publish(
                image_url=None if kind == "reel" else x["_url"],
                video_url=x["_url"] if kind == "reel" else None,
                caption=x.get("caption", ""), kind=kind)
            state["posted"][x["id"]] = {"media_id": mid, "at": datetime.now(TZ).isoformat(),
                                        "slot": x["slot"], "theme": x.get("theme")}
            used += 1
            crosspost_facebook(x, cfg, state, graph, st or 3)
            state["failed"].pop(x["id"], None)
            print(f"  ✔ {x['id']} -> {mid}")
            h["consecutive_other"] = 0
        except Exception as e:
            errors += 1
            f = state["failed"].setdefault(x["id"], {"attempts": 0})
            f["attempts"] += 1
            f["error"] = str(e)[:300]
            print(f"  ✖ {x['id']}: {f['error']}")
            kind = getattr(e, "kind", "other")
            if kind != "other":                       # Meta pushed back: stop immediately
                health.pause(h, kind, str(e))
                save_json(STATE, state)
                break
            h["consecutive_other"] = h.get("consecutive_other", 0) + 1
            if h["consecutive_other"] >= 3:
                health.pause(h, "other", f"3 failures in a row; last: {e}")
                save_json(STATE, state)
                break
        save_json(STATE, state)
        health.save(h)
    return 0  # problems are handled by auto-pause + notification, not by failing the job


if __name__ == "__main__":
    sys.exit(main())
