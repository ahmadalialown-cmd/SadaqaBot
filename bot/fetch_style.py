"""Download the account's recent posts (images, carousel children, video thumbnails,
captions, like counts) into style_refs/ (gitignored) for style/caption tuning."""
import json
from pathlib import Path

import requests

import envload
import graph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "style_refs" / "api"


def main(limit=40):
    envload.load()
    ok, warn = graph.token_status()
    print("token ok:", ok, "|", warn or "no expiry warning")
    print("account: @" + graph.username())
    OUT.mkdir(parents=True, exist_ok=True)
    items = graph.recent_media(limit)
    (OUT / "posts.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    n = 0
    for it in items:
        urls = []
        if it.get("children"):
            urls = [(f"{it['id']}_{i}", c.get("media_url") if c["media_type"] == "IMAGE" else c.get("thumbnail_url"))
                    for i, c in enumerate(it["children"]["data"])]
        else:
            urls = [(it["id"], it.get("media_url") if it["media_type"] == "IMAGE" else it.get("thumbnail_url"))]
        for name, u in urls:
            if u:
                (OUT / f"{name}.jpg").write_bytes(requests.get(u, timeout=60).content)
                n += 1
    print(f"posts: {len(items)}, images saved: {n} -> {OUT}")


if __name__ == "__main__":
    main()
