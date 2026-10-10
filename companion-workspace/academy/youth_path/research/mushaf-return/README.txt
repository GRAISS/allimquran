ALLIM: return from fullscreen Mushaf — 2026-10-10

STATUS: Prepared and locally checked. No PR, merge or production deployment.

Changed source files in /Users/rafael/Documents/ChatGPT/Арабский:
index.html, styles.css, app.js. Original copies: before/.
source.patch targets companion-workspace/ in the application repository.
No shared application, Blog or LMS changes.

Behavior:
An always-visible top navigation row contains “В приложение” / “Back to app” /
“العودة إلى التطبيق” and the existing home link. The 44px targets are keyboard
accessible. RTL mirrors the return arrow and row order. Exit stops recognition
and verse audio, restores regular reading navigation, preserves the selected
verse/page state and moves focus to the Quran search control.

Reproducible database-held page patch:
After the owner confirms the agreed commit manifest and base, put mushaf_return.py
and payload.json together inside the application, in allimquran/mushaf_return/;
rename mushaf_return.py to __init__.py. Review via GRAISS fork / separate
codex/allimquran-mushaf-return branch / PR to g-karim/allimquran:main.
Do not alter or replace existing PRs 1/2 or existing branches.

Local installation check (owner-approved bench/site only):
bench --site allimquran.localhost execute allimquran.mushaf_return.execute
The default is dry-run. After review, apply on that test site:
bench --site allimquran.localhost execute allimquran.mushaf_return.execute --kwargs '{"apply": true}'
Repeat dry-run: changed_fields must be empty. The patch fails on unsupported
anchors rather than replacing an entire page. It uses normal document write
permissions. Production release remains the responsibility of g-karim.

Checks actually performed:
- JavaScript syntax: app.js and patched public-page JavaScript passed.
- Pure page transformation against downloaded public HTML and local source;
  idempotent; one exit control.
- Browser: local reproduction of public page, 320x700 and 390x844 RU,
  768x1024 and 1280x900 EN, 390x844 and 1280x900 AR.
- Button visible, 44px height, no horizontal overflow, Enter exits Mushaf,
  navigation restored, focus restored, selected verse preserved in all cases.
- Existing local source also checked via mouse click at 390x844.
- No browser error entries captured in the final preview check.
Evidence: browser-checks.json, patch-checks.json, mobile-preview.jpg.

Limits:
colleague-projects.json was not provided/found; no agreed commit comparison,
installation or database migration run, and no PR created.
Browser reproduction uses a static local server without Quran API or speech
services. Return works while page content is loading/unavailable. Full Quran
page loading, live recognition/audio, auth, integrations and database writes
were not tested. Screenshot is a local preview, not a deployed change.
Public-preview.html/public-patched.js are QA artifacts; do not deploy them.
Use only the narrow source.patch and reviewed page patch/payload.
