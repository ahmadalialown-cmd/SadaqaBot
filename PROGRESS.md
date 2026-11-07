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

## 2026-11-07 (evening)
- The secrets are stored (IG_TOKEN, IG_USER_ID, PAGE_ID, META_APP_ID, META_APP_SECRET) plus `.env`. The token is valid, `graph.username()` = 9d8h0garyh, and there's no expiry warning.
- Run secrets via `setup_secrets.ps1`: Store Python can't read gh's keyring, so the wrapper passes GH_TOKEN.
- Fetched 17 real posts into style_refs/api (gitignored). Findings: mostly no caption; the captions that exist are duas for Saud by name + "#قرآن #ذكر". Captions now rotate the account's own two duas verbatim. Dua posts use a lighter weight.
- The review page for 2026-11-08..14 (85 items) has been generated and opened. **WAITING for the user's approval.**

## 2026-11-07 (night): plan change from the user
- Daily Maghrib feed = one athar from كتاب الزهد للإمام أحمد.
  - Text: OpenITI copy of Shamela 8494 (دار الكتب العلمية ط1 1420هـ), in data/zuhd/zuhd.md.
  - 85 curated athar in data/athar.yaml (bot/build_athar.py; speakers verified against the isnad). Each matn is an exact substring, with only ms/[ص:] markers removed.
  - The source line cites the narration number + edition. Pages are omitted because the digital page tags are inconsistent.
  - 77 used for 90 days, no repeats; 8 spare.
- Adhkar stories = the account's own carousels (config adhkar_posts: morning 20 / evening 13 / sleep 16 slides), turned into 1080x1920 frames in media/adhkar by bot/adhkar_stories.py.
  - That's 49 stories/day. The publish quota is checked (limit 100/24h) and feed posts go first.
- The old adhkar story designs and daily verse/hadith posts were removed. Friday (Asr salawat + Saud dua) is unchanged.
- The review page for week 1 has been regenerated. **WAITING for approval.**

## 2026-11-07: LAUNCHED
- Test story 18121670383782458 published and verified. Schedule */30 is on, `paused: false`. Week 1 is approved.

## Growth layer (requested 2026-11-07), status
- Done:
  - bot/reel_maker.py: text reveal, hook visible at 0 s, seamless loop, silence or locally synthesised ambience. No music.
  - 3 sample reels (media/reels/samples) in the review page, awaiting approval.
  - captions.share_caption: send-CTA variants + ≤5 hashtags per theme.
- Blocked or needs the user:
  - Recitation audio: no clear reuse licence found (everyayah has no explicit licence; some reciters UNKNOWN). Needs a source with explicit permission.
  - Insights: the token lacks instagram_manage_insights / read_insights, so a token regen with those scopes is needed for the weekly loop.
  - Threads API: Meta app use case + user OAuth.
  - YouTube: Google Cloud project + OAuth consent (user).
- Next after sample approval:
  - Reel scheduling by weekday rotation + Hijri seasons.
  - Shareable series data (authentic duas with refs).
  - FB Page cross-post (page token already stored).
  - Weekly report_AR.md + re-weighting.

## Growth layer, built (samples approved 2026-11-07)
- bot/reels_plan.py: 1 reel/day at 20:30 (reels_per_day 2 adds the athar at 13:00).
  - Sat/Mon/Wed: athar. Sun/Tue: verse + As-Sa'di (28 exact lines, data/reels_content.yaml). Thu: share-dua (deceased/sick/parents). Fri: Friday + Saud.
  - Hijri seasons via hijridate (Ramadan 1448 starts 2027-02-08, just after the current bank).
- 90 reel specs are in the bank (pending). Videos are rendered on review/approval; week-1 reels are rendered for review.
- FB cross-post code (fb_photo / fb_reel) exists, but config crosspost.facebook=false until the token has pages_manage_posts.
- weekly.yml (Fri 10:30 UTC) runs weekly_report.py → report_AR.md + chart + data/optimizer.json (best reel time is applied at approval) + Trial Reels reminder at 200 followers. It currently reports missing insights/comments scopes.
- NOT done (needs the user):
  - Threads API auth + code.
  - YouTube OAuth + code.
  - Token regen with instagram_manage_insights, instagram_manage_comments, pages_manage_posts (add them to the app use case first).
  - Licensed recitation source.

## 2026-11-07 (late): PAUSED — Facebook account locked
- The token was regenerated with insights/comments/pages_manage_posts and crosspost.facebook was turned on. Insights for the 17 posts were pulled.
- Then Meta put the FB account behind a security checkpoint ("may have been compromised"). The API returns OAuthException 190 ("log in to facebook.com…").
- Set `paused: true`. The Threads setup was stopped mid-way (the Threads use case is already added to the app).
- To resume:
  1. The user unlocks on a device they used before.
  2. Check the token (`graph.token_status()`); if invalid, regenerate it in Explorer and run setup_secrets.ps1.
  3. Set `paused: false`.
  4. Re-approve/reschedule the missed week-1 items if needed. max_late is 90 min, so missed slots are skipped, not posted late.
- Keep browser automation on Meta sites to a minimum from now on.
- User instruction (2026-11-07): Instagram is asking for selfie-video verification (the user is doing it).
  - Stay paused. No Meta/API actions that day. The weekly-report workflow is disabled (`gh workflow disable weekly.yml`).
  - The publish workflow keeps running but exits at the `paused` check before any API call.
  - Resume slowly in a few days, starting with ONE post per day (no story bursts), then ramp up.

## Next after the user says تم
1. Verify the Secrets exist (`gh secret list`) and query `me/accounts` in Explorer.
2. Fetch the last ~40 posts into `style_refs/`, analyse them, tune `render.STYLE` and `captions.py`, then make a side-by-side comparison.
3. Rebuild the bank's captions (`build_bank.py` keeps statuses; caption regen is still to add), regenerate the review page and show it.
4. After approval: `approve.py --days 7`, then commit/push.
5. Run a dry run on Actions, get the user's OK, then `publish.py --only <story id>` for one test story and verify it via `graph.media_info`.
6. Add `schedule: cron */30` and set `paused: false`, then tell the user what's running and the next post time.
