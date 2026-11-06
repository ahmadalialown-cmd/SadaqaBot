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

GRAPH = "https://graph.facebook.com/v24.0"
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


def main():
    print("الصق القيم هنا (ما راح تبين وانت تلصق، عادي):")
    app_id = input("App ID: ").strip()
    app_secret = getpass.getpass("App Secret: ").strip()
    short = getpass.getpass("User token من Graph API Explorer: ").strip()

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
    print("خلصنا. ارجع لـ Claude واكتب: تم")


if __name__ == "__main__":
    main()
