"""Interactive token setup. The user pastes values into hidden prompts;
nothing is printed in full, nothing is written to tracked files.

Flow: short-lived user token + app id/secret -> long-lived user token
-> long-lived Page token -> instagram_business_account id.
Results go to GitHub Actions Secrets (gh secret set, via stdin) and to a local .env.
"""
import getpass
import subprocess
import sys
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com/v27.0"
ROOT = Path(__file__).resolve().parents[1]


def mask(v: str) -> str:
    return v[:4] + "…" + v[-4:] if len(v) > 12 else "****"


def g(path, **params):
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=30)
    data = r.json()
    if "error" in data:
        sys.exit(f"Graph error: {data['error'].get('message')}")
    return data


def gh_secret(name, value):
    subprocess.run(["gh", "secret", "set", name], input=value.encode(), check=True, cwd=ROOT)
    print(f"  ✔ GitHub secret {name} = {mask(value)}")


DEFAULT_APP_ID = "1138534398890777"


def clipboard(value=None):
    if value is None:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                             capture_output=True, text=True, encoding="utf-8")
        return (out.stdout or "").strip()
    subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ' '"], check=False)


def read_secret(label):
    """Hidden paste, or just press Enter to take it from the clipboard."""
    v = getpass.getpass(f"{label} (الصقه، أو انسخه واضغط Enter بس): ").strip()
    if not v:
        v = clipboard()
    if not v:
        sys.exit(f"ما وصلني {label}.")
    print(f"  ✔ وصل ({len(v)} حرف)")
    return v


def main():
    app_id = input(f"App ID [{DEFAULT_APP_ID}]: ").strip() or DEFAULT_APP_ID
    app_secret = read_secret("App Secret")
    short = read_secret("User token من Graph API Explorer")
    clipboard("")

    ll = g("oauth/access_token", grant_type="fb_exchange_token",
           client_id=app_id, client_secret=app_secret, fb_exchange_token=short)["access_token"]

    pages = g("me/accounts", access_token=ll, fields="id,name,access_token,instagram_business_account")["data"]
    pages = [p for p in pages if p.get("instagram_business_account")]
    if not pages:
        sys.exit("ما لقيت صفحة فيسبوك مربوطة بحساب انستقرام بزنس.")
    for i, p in enumerate(pages):
        print(f"  [{i}] {p['name']}")
    page = pages[int(input("رقم الصفحة: ") or 0)] if len(pages) > 1 else pages[0]

    ig_id = page["instagram_business_account"]["id"]
    page_token = page["access_token"]  # page token derived from a long-lived user token does not expire
    ig = g(ig_id, fields="username", access_token=page_token)
    print(f"  ✔ Instagram: @{ig.get('username')}  (id {ig_id})")

    vals = {"IG_USER_ID": ig_id, "PAGE_ID": page["id"], "IG_TOKEN": page_token,
            "META_APP_ID": app_id, "META_APP_SECRET": app_secret}
    for k, v in vals.items():
        gh_secret(k, v)
    (ROOT / ".env").write_text("".join(f"{k}={v}\n" for k, v in vals.items()), encoding="utf-8")
    print("  ✔ .env محلي (مو مرفوع على GitHub)")
    clipboard("")
    print("خلصنا. ارجع لـ Claude واكتب: تم")


if __name__ == "__main__":
    main()
