"""Load the local .env (gitignored) into os.environ without printing anything."""
import os
from pathlib import Path


def load():
    p = Path(__file__).resolve().parents[1] / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
