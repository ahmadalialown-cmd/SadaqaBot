"""Turn the account's own adhkar carousel posts into story frames.

For each session (morning/evening/sleep) in config.yaml `adhkar_posts`, fetch the post's
carousel children IN ORDER via the API, download each slide, and centre it on a
1080x1920 canvas in the account's background colour -> media/adhkar/<session>_NN.png.
Writes data/adhkar_frames.json (session -> list of frame paths). Re-run whenever the
user edits those posts."""
import io
import json
from pathlib import Path

import requests
import yaml
from PIL import Image

import envload
import graph
from render import STYLE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "media" / "adhkar"
INDEX = ROOT / "data" / "adhkar_frames.json"


def to_story(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    w = 1080
    img = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
    # sample the slide's own background so the letterbox blends in seamlessly
    canvas = Image.new("RGB", (1080, 1920), img.getpixel((8, 8)) or STYLE["bg"])
    canvas.paste(img, (0, (1920 - img.height) // 2))
    return canvas


def main():
    envload.load()
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for session, pid in cfg["adhkar_posts"].items():
        kids = graph._call("GET", pid, fields="children{media_type,media_url}")["children"]["data"]
        paths = []
        for i, c in enumerate(kids, 1):
            if c["media_type"] != "IMAGE":
                continue
            img = Image.open(io.BytesIO(requests.get(c["media_url"], timeout=60).content))
            p = OUT / f"{session}_{i:02d}.png"
            to_story(img).save(p, optimize=True)
            paths.append(p.relative_to(ROOT).as_posix())
        index[session] = {"post_id": pid, "frames": paths}
        print(f"{session}: {len(paths)} frames")
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
