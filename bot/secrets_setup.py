"""Interactive token setup. The user pastes values into hidden prompts;
nothing is printed in full, nothing is written to tracked files.

Flow: short-lived user token + app id/secret -> long-lived user token
-> long-lived Page token -> instagram_business_account id.
Results go to GitHub Actions Secrets (gh secret set, via stdin) and to a local .env.
"""
import getpass
import re
import subprocess
import sys
from pathlib import Path

import requests
import yaml

GRAPH = "https://graph.facebook.com/v27.0"
ROOT = Path(__file__).resolve().parents[1]


def mask(v: str) -> str:
    return f"<{len(v)} chars>"


def g(path, **params):
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=30)
    data = r.json()
    if "error" in data:
        sys.exit(f"Graph error: {data['error'].get('message')}")
    return data


REPO = "ahmadalialown-cmd/SadaqaBot"


def gh_exe():
    import shutil
    for c in (shutil.which("gh"), r"C:\Program Files\GitHub CLI\gh.exe"):
        if c and Path(c).exists():
            return c
    sys.exit("✖ ما لقيت GitHub CLI (gh). سكّر PowerShell وافتحه من جديد، وجرّب مرة ثانية.")


def check_gh():
    r = subprocess.run([gh_exe(), "auth", "status"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("✖ GitHub ما وصل للسكربت. شغّله بهالطريقة:\n"
                 "   powershell -ExecutionPolicy Bypass -File C:\\SadaqaBot\\setup_secrets.ps1")
    print("  ✔ GitHub جاهز")


def gh_secret(name, value):
    subprocess.run([gh_exe(), "secret", "set", name, "--repo", REPO], input=value.encode(),
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
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


SECRET_RE = re.compile(r"^[0-9a-fA-F]{32}$")
TOKEN_RE = re.compile(r"^EAA[0-9A-Za-z]{50,}$")


def classify(a, b):
    """Return (app_secret, user_token) whatever order they were given in."""
    for s, t in ((a, b), (b, a)):
        if SECRET_RE.match(s) and TOKEN_RE.match(t):
            if s is b:
                print("  ↺ القيمتين كانوا مقلوبين، عدّلتهم.")
            return s, t
    for v in (a, b):
        if not (SECRET_RE.match(v) or TOKEN_RE.match(v)):
            sys.exit(f"✖ فيه قيمة ({len(v)} حرف) شكلها غلط: لا هي App Secret (32 حرف/رقم) "
                     "ولا توكن (يبدأ بـ EAA). انسخها من جديد.")
    if SECRET_RE.match(a) and SECRET_RE.match(b):
        sys.exit("✖ القيمتين App Secret. انسخ التوكن من Graph API Explorer (زر النسخ جنب التوكن).")
    sys.exit("✖ القيمتين توكن. انسخ App Secret من إعدادات التطبيق ← أساسي ← Show.")


def check_token(app_id, app_secret, token):
    r = requests.get(f"{GRAPH}/debug_token", timeout=30, params={
        "input_token": token, "access_token": f"{app_id}|{app_secret}"}).json()
    if "error" in r:
        msg = r["error"].get("message", "")
        if "client secret" in msg.lower() or r["error"].get("code") in (1, 101):
            sys.exit("✖ الـ App Secret غلط أو مو حق تطبيق SadaqaBot. انسخه من جديد من الإعدادات ← أساسي.")
        sys.exit(f"✖ Meta رفضت الفحص: {msg}")
    d = r.get("data", {})
    if str(d.get("app_id")) != str(app_id):
        sys.exit("✖ التوكن مو حق تطبيق SadaqaBot. اختار SadaqaBot في Graph API Explorer وسوّ توكن جديد.")
    if not d.get("is_valid"):
        sys.exit("✖ التوكن منتهي أو ملغي. اضغط Generate Access Token من جديد وانسخه.")
    need = {"instagram_basic", "instagram_content_publish", "pages_show_list"}
    missing = need - set(d.get("scopes", []))
    if missing:
        sys.exit(f"✖ التوكن ناقصه صلاحيات: {', '.join(sorted(missing))}. سوّ توكن جديد ووافق عليها.")
    print("  ✔ التوكن صالح وفيه الصلاحيات المطلوبة")


def main():
    check_gh()  # before asking for any value
    app_id = input(f"App ID [{DEFAULT_APP_ID}]: ").strip() or DEFAULT_APP_ID
    first = read_secret("القيمة الأولى (App Secret أو التوكن)")
    second = read_secret("القيمة الثانية")
    clipboard("")
    if first == second:
        sys.exit("✖ نسخت نفس القيمة مرتين. انسخ الثانية واضغط Enter.")
    app_secret, short = classify(first, second)
    check_token(app_id, app_secret, short)

    ll = g("oauth/access_token", grant_type="fb_exchange_token",
           client_id=app_id, client_secret=app_secret, fb_exchange_token=short)["access_token"]

    target = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))["instagram_username"]
    pages = g("me/accounts", access_token=ll,
              fields="id,name,access_token,instagram_business_account{id,username}")["data"]
    if not pages:
        sys.exit("✖ التوكن ما فيه أي صفحة فيسبوك. سوّ توكن جديد واختار صفحة «صدقة جارية» في النافذة.")
    linked = [p for p in pages if p.get("instagram_business_account")]
    match = [p for p in linked if p["instagram_business_account"].get("username") == target]
    if not match:
        found = ", ".join("@" + p["instagram_business_account"].get("username", "?") for p in linked) or "ولا حساب"
        sys.exit(f"✖ لازم يكون @{target} مربوط بالصفحة، بس اللي لقيته: {found}. "
                 "اربط الحساب بالصفحة (إعدادات الصفحة ← الحسابات المرتبطة ← Instagram) وسوّ توكن جديد.")
    page = match[0]
    ig_id = page["instagram_business_account"]["id"]
    page_token = page["access_token"]  # page token from a long-lived user token does not expire
    ig = g(ig_id, fields="username", access_token=page_token)
    if ig.get("username") != target:
        sys.exit(f"✖ الحساب المربوط مو @{target}. وقفت ولا حفظت شي.")
    print(f"  ✔ Instagram: @{ig['username']}  (id {ig_id}) · الصفحة: {page['name']}")

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
