# SadaqaBot — Progress (paused 2026-11-06)

Automated Instagram publishing for the «صدقة جارية» account (for the late Saud Al-Qahtani, رحمه الله).
Original full spec: the pasted prompt (STEP 1–9 + FINISH). This file is the resume point.

## Status: PAUSED — nothing can publish
- No GitHub Actions workflows exist (no `.github/workflows/`), so no schedule is running.
- No publishing code exists yet, and no Meta tokens or GitHub Secrets have been set.
- No `.env` exists. Secrets must never be committed (`.env` is gitignored).

## Done
1. Tools installed: Python 3.13 (venv at `.venv`, gitignored), playwright + Chromium, pyyaml, requests, pillow; git, GitHub CLI, ffmpeg (winget).
2. GitHub: `gh` logged in as `ahmadalialown-cmd`. Public repo created: https://github.com/ahmadalialown-cmd/SadaqaBot (branch `main`).
3. `data/quran-uthmani.txt`: Tanzil Uthmani text with tashkeel, format `surah|ayah|text`, 6236 verses verified. Keep Tanzil attribution and do not modify the text.
4. `bot/prayer.py`: offline Doha prayer times (Fajr 18°, Isha = Maghrib+90, Asr factor 1). Checked 2026-11-06 against the "Qatar" (Awqaf) method on timesprayer.com: Fajr 04:27, Dhuhr 11:17, Asr 14:27, Maghrib 16:51, Isha 18:21 (exact match; sunrise off by 1 min). The Ministry's own site was not machine-readable.
5. `bot/secrets_setup.py`: the user pastes the App ID, App Secret and short-lived user token into hidden prompts. The script exchanges the user token for a long-lived one, then gets the Page token and the IG business id, stores them via `gh secret set` (stdin) and in a local `.env`. Claude never handles tokens.

## Stopped at
**STEP 2 — Facebook login.** The login page was open in the built-in browser and the user had not signed in yet.

## Remaining, in order
1. User signs in to Facebook (themselves). If needed, the user registers as a Meta developer and accepts the Platform Terms (themselves).
2. Confirm the IG account is Business and linked to a FB Page. Ask before creating a Page «صدقة جارية» if there isn't one.
3. Create a Meta app (Business type) and add Instagram Graph API / Facebook Login for Business. Permissions: instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement, business_management.
4. User generates a token in Graph API Explorer, then runs `.venv\Scripts\python bot\secrets_setup.py` and pastes the values there. Then add a token-expiry check and warning.
5. STEP 3: download the last ~40 posts into `style_refs\` (gitignored) and analyze the style.
6. STEP 4: HTML/CSS + Playwright renderer (feed 1080x1350, story 1080x1920) with a bundled Naskh font. Make a side-by-side comparison with the real posts and iterate.
7. STEP 5: content bank (~90 days): Quran from the local file only, Hisn al-Muslim adhkar, and only hadith that are Sahih/Hasan with a verified source. Every item has status pending/approved.
8. STEP 6: publish script + GitHub Actions every 30 min (create it **disabled / manual-only** until launch). State file, no double-posts, retries.
9. STEP 7: review.html for the next 7 days; user approves. `auto_approve=false`.
10. STEP 8: reels helper (ffmpeg, reels_inbox).
11. STEP 9: dry run, then the user's OK, then ONE test story, verify it, then enable the schedule.
12. FINISH: README_AR.md, and tell the user what's running and when the next post goes out.
