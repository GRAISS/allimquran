# ALLIM mobile Mushaf — review package

Prepared locally on 11 October 2026; handed off for review on 13 October 2026.

On a 390px phone viewport, the public reader's dense page used 17–22px page-font glyphs. This candidate adds a separate adaptive reading layout with 36px text by default on narrow screens, immediate A−/A+ controls (28–52px), saved preferences and preservation of the visible reading position. The original page layout remains selectable. It retains the previous return-to-app control and selected verse.

It also adds page-load retry and Enter-to-jump, corrects stale/failed navigation, prevents pinch/vertical gestures from turning pages, and provides localized controls in EN/AR/RU/TR/TG/UZ/TT. New controls have 44px touch targets. No Quran text, pronunciation assessment, recognition service, Blog, LMS or shared application changes are proposed.

## Review status

This is an uninstalled candidate, not a production-ready release. The agreed `colleague-projects.json` is still unavailable. The recorded local reference commit is **not** an approved installation or PR base. Please reconcile the patch with the agreed source before integration, then verify installation/migration on `allimquran.localhost`. Review, merge and deployment remain with Karim.

## Contents and application

- `canonical-source.patch`: primary patch for the three app-owned `allimquran/website_content/pages/learn/` source fields. Includes the earlier return-to-app patch to preserve a visible exit. Check for overlap with issue #3 before integration.
- `canonical/`: candidate source fields for inspection; do not overwrite newer source blindly.
- `source.patch`: separate diff for the standalone companion workspace, including cache v93. The standalone and canonical baselines differ; this is not an alternative whole-page production deployment.
- `reader.{html,css,js}`: focused controls and reader behavior.
- `reader.test.cjs` and `fixtures/`: repeatable behavior tests against the candidate canonical JavaScript.
- `provenance.json`: original local reference and before/after SHA-256 values.
- `browser-checks.json`: local browser evidence from 11 October, not an installation result.

After confirming the agreed base: run `git apply --check canonical-source.patch`, reconcile any drift, apply only the reviewed changes, use the application's guarded source-sync workflow on the local test site, run migration and verify idempotence. Open the implementation PR from a dedicated GRAISS fork branch to `g-karim/allimquran:main` after those gates pass.

## Validation

`node reader.test.cjs` and `node --check canonical/javascript.js` can run without additional npm dependencies. The regression suite checks preference validation/persistence, storage denial, exact Unicode/glyph round trips, stale responses, failed navigation, and gesture guards. Fixtures cover 288 words/markers across pages 1, 2, 3 and 604.

Prior local browser QA covered both standalone and canonical candidates, widths 320/390/430/768/1280 and 844×390 landscape; EN/AR/RU and RTL; size limits and reload persistence; page boundaries; error/retry; selected verse and keyboard focus after exit; reading-anchor preservation; no horizontal overflow in the checked states. Existing local reading-journal, memory-journey and offline-cache tests passed.

Not verified: agreed-site installation/migration, physical iPhone/Safari/pinch behavior, live microphone/ASR quality, audio playback, authentication, account sync or production integrations. The isolated preview used fixed public Quran fixtures and intentionally unavailable unrelated APIs. No production edits or deployments were made.

## Sources

- Tarteel adaptive font-size workflow: https://support.tarteel.ai/en/articles/12414378-changing-font-size-adaptive-mode
- Tarteel adaptive reading: https://support.tarteel.ai/en/articles/12414381-adaptive-mode
- Quran fixtures: existing Quran Foundation Content API, `https://api.quran.com/api/v4/verses/by_page/{page}` with word fields `code_v1,code_v2,text_qpc_hafs,line_number,page_number`, Mushaf 2. Test snapshots only, not a new runtime corpus; retain the project's existing content attribution and licensing requirements.
