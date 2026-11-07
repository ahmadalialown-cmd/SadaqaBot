"""Minimal Instagram Graph API client (Facebook-login flavour, Page token)."""
import os
import time
from datetime import datetime, timezone

import requests

GRAPH = "https://graph.facebook.com/v27.0"


class GraphError(Exception):
    def __init__(self, msg, code=None, subcode=None):
        super().__init__(msg)
        self.code, self.subcode = code, subcode

    @property
    def kind(self):
        """auth | rate_limit | blocked | permission | other — drives the self-healing policy."""
        c, s = self.code, self.subcode
        if c == 368:                                    # temporarily blocked for policy/spam
            return "blocked"
        if c in (190, 102):                             # token invalid / account checkpoint
            return "auth"
        if c in (4, 17, 32, 613, 80001, 80002) or s in (2207042,):
            return "rate_limit"
        if s in (2207051, 2207050, 1390008):     # action blocked / spam / account restricted
            return "blocked"
        if c in (10, 200, 3):
            return "permission"
        return "other"


def _env(name):
    v = os.environ.get(name)
    if not v:
        raise GraphError(f"missing env {name}", code=190)
    return v


def _call(method, path, **params):
    params.setdefault("access_token", _env("IG_TOKEN"))
    r = requests.request(method, f"{GRAPH}/{path}", params=params, timeout=60)
    data = r.json()
    if "error" in data:
        e = data["error"]
        # never echo params (they contain the token)
        raise GraphError(f"{e.get('type')} {e.get('code')}/{e.get('error_subcode')}: {e.get('message')}",
                         e.get("code"), e.get("error_subcode"))
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


def token_scopes():
    app = f"{_env('META_APP_ID')}|{_env('META_APP_SECRET')}"
    return set(_call("GET", "debug_token", input_token=_env("IG_TOKEN"), access_token=app)["data"].get("scopes", []))


# ---- Facebook Page cross-posting (needs pages_manage_posts) ----
def fb_photo(image_url, caption):
    return _call("POST", f"{_env('PAGE_ID')}/photos", url=image_url, caption=caption)["id"]


def fb_reel(video_url, description):
    page = _env("PAGE_ID")
    start = _call("POST", f"{page}/video_reels", upload_phase="start")
    vid = start["video_id"]
    r = requests.post(start["upload_url"], timeout=120,
                      headers={"Authorization": f"OAuth {_env('IG_TOKEN')}", "file_url": video_url})
    if r.status_code >= 300:
        raise GraphError(f"fb reel upload {r.status_code}")
    _call("POST", f"{page}/video_reels", upload_phase="finish", video_id=vid,
          video_state="PUBLISHED", description=description)
    return vid


# ---- Insights (need instagram_manage_insights; comments need instagram_manage_comments) ----
def media_insights(media_id, metrics):
    out = {}
    for m in metrics:  # one by one: unsupported metrics for a media type shouldn't kill the rest
        try:
            d = _call("GET", f"{media_id}/insights", metric=m)["data"]
            out[m] = d[0]["values"][0]["value"] if d and d[0].get("values") else d[0].get("total_value", {}).get("value")
        except GraphError:
            pass
    return out


def media_comments(media_id):
    try:
        return _call("GET", f"{media_id}/comments", fields="text,timestamp,username").get("data", [])
    except GraphError:
        return []


def account_info():
    return _call("GET", _env("IG_USER_ID"), fields="username,followers_count,media_count")


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
