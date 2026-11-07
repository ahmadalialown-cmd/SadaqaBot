# SadaqaBot — Progress (updated 2026-11-07)

## Status: built, waiting on the user — NOTHING can publish
- `config.yaml`: `paused: true`, `auto_approve: false`.
- `.github/workflows/publish.yml` is manual-only (no `schedule:`); its default is dry-run.
- Every bank item is `pending`. No GitHub Secrets yet, and no `.env`.

## Done
- Tools: Python venv, Playwright + Chromium, git, gh, ffmpeg.
- Public repo `ahmadalialown-cmd/SadaqaBot`.
- Meta app **SadaqaBot** (id 1138534398890777) uses the Instagram API with Facebook login. Content permissions are added; Graph API Explorer has the 5 permissions.
- Facebook Page **صدقة جارية** created (id 61596428126472, category منظمة دينية).
- `bot/secrets_setup.py` takes the values in any order, validates their shape, the token and its scopes, and prints no values.
- Content:
  - `data/quran-uthmani.txt` + `quran-data.xml` (Tanzil); the basmala is stripped from ayah 1 and «إبراهيم» is fixed.
  - `data/hisn/*.json` (hisnmuslim.com API): morning/evening, sleep, and duas for the deceased. Quranic adhkar use the Tanzil text.
  - `data/verses.yaml` (82 refs) and `data/hadith.yaml` (3 sahih, flagged needs_review).
  - `data/bank.json` = 90 days from 2026-11-08: 1093 items (11 story frames/day + Maghrib feed + Friday Asr), all pending.
- Code:
  - `render.py`: Amiri for text, Amiri Quran for Uthmani; feed 1080x1350 and story 1080x1920 with auto-fit to the safe area.
  - `prayer.py`: Qatar method, verified.
  - `publish.py`: dry-run, `--only`, no double posts, retries, max-late window, token-expiry warning.
  - `graph.py`, `approve.py`, `review.py`, `reels.py` (ffmpeg letterbox + verse overlay, tested).
  - `tests/test_content.py` all pass. `README_AR.md` written.

## Blocked on the user (checklist sent)
0. TARGET ACCOUNT = **@9d8h0garyh** (display name «صَدقة», 17 posts, Accounts Center id 17841446695660671). It is a **Creator** account (user asked to be told how to switch to Business). `secrets_setup.py` and `publish.py` refuse any other username.
1. Link @9d8h0garyh to the Page «صدقة جارية» (checked 2026-11-07: nothing linked yet). The IG confirm step is a popup that only opens from the user's click.
2. Generate a new token in Explorer with the Page + IG selected, then run `secrets_setup.py` (the user copies the values; Claude must not).

## 2026-11-07 (later)
- @9d8h0garyh confirmed **Business**. Page «صدقة جارية» = Page id 1428399470356408. The IG link was started in Business Suite (settings → profiles → page → «ربط بحساب Instagram» → «تسجيل الدخول إلى Instagram» → «متابعة»), but the final IG window is a popup that only opens from the user's click.
- The style is tuned against the real slides (style_refs/ref_*.png; out/compare.png):
  - Noto Naskh 600, title on top + rule, clause-per-line text, count at the bottom.
  - Quran from the Tanzil *simple* script (as the account uses), split at pause marks, no ayah numbers, no basmala on adhkar slides.
  - The bank was rebuilt (still all pending).

## Next after the user says تم
1. Verify the Secrets exist (`gh secret list`) and query `me/accounts` in Explorer.
2. Fetch the last ~40 posts into `style_refs/`, analyse them, tune `render.STYLE` and `captions.py`, then make a side-by-side comparison.
3. Rebuild the bank's captions (`build_bank.py` keeps statuses; caption regen is still to add), regenerate the review page and show it.
4. After approval: `approve.py --days 7`, then commit/push.
5. Run a dry run on Actions, get the user's OK, then `publish.py --only <story id>` for one test story and verify it via `graph.media_info`.
6. Add `schedule: cron */30` and set `paused: false`, then tell the user what's running and the next post time.
