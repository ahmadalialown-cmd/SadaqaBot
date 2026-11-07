"""Minimal Instagram Graph API client (Facebook-login flavour, Page token)."""
import os
import time
from datetime import datetime, timezone

import requests

GRAPH = "https://graph.facebook.com/v27.0"


class GraphError(Exception):
    pass


def _env(name):
    v = os.environ.get(name)
    if not v:
        raise GraphError(f"missing env {name}")
    return v


def _call(method, path, **params):
    params.setdefault("access_token", _env("IG_TOKEN"))
    r = requests.request(method, f"{GRAPH}/{path}", params=params, timeout=60)
    data = r.json()
    if "error" in data:
        e = data["error"]
        # never echo params (they contain the token)
        raise GraphError(f"{e.get('type')} {e.get('code')}: {e.get('message')}")
    return data


def token_status():
    """Returns (ok, warning_text_or_None)."""
    app = f"{_env('META_APP_ID')}|{_env('META_APP_SECRET')}"
    d = _call("GET", "debug_token", input_token=_env("IG_TOKEN"), access_token=app)["data"]
    if not d.get("is_valid"):
        return False, "التوكن منتهي أو ملغي — شوف README_AR.md (إذا انتهى التوكن)."
    warn = None
    now = datetime.now(timezone.utc).timestamp()
    for key in ("expires_at", "data_access_expires_at"):
        ts = d.get(key) or 0
        if ts and ts - now < 14 * 86400:
            days = int((ts - now) // 86400)
            warn = f"تنبيه: صلاحية التوكن ({key}) تنتهي بعد {days} يوم — جدّده من README_AR.md."
    return True, warn


def publish(image_url=None, video_url=None, caption="", kind="feed"):
    """kind: feed | story | reel. Returns the published media id."""
    ig = _env("IG_USER_ID")
    params = {}
    if kind == "story":
        params["media_type"] = "STORIES"
    elif kind == "reel":
        params["media_type"] = "REELS"
    if video_url:
        params["video_url"] = video_url
    else:
        params["image_url"] = image_url
    if kind != "story" and caption:
        params["caption"] = caption
    cid = _call("POST", f"{ig}/media", **params)["id"]
    for _ in range(60 if video_url else 20):
        st = _call("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            raise GraphError(f"container {st}")
        time.sleep(5)
    return _call("POST", f"{ig}/media_publish", creation_id=cid)["id"]


def publishing_quota():
    """-> (used, total) for the rolling 24h API publishing limit."""
    d = _call("GET", f"{_env('IG_USER_ID')}/content_publishing_limit",
              fields="quota_usage,config").get("data", [{}])[0]
    return d.get("quota_usage", 0), (d.get("config") or {}).get("quota_total", 100)


def username():
    return _call("GET", _env("IG_USER_ID"), fields="username").get("username")


def media_info(media_id):
    return _call("GET", media_id, fields="id,media_type,media_product_type,permalink,timestamp")


def recent_media(limit=40):
    ig = _env("IG_USER_ID")
    fields = ("id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,"
              "timestamp,like_count,comments_count,children{media_type,media_url,thumbnail_url}")
    return _call("GET", f"{ig}/media", fields=fields, limit=limit).get("data", [])
