ALLIM youth reading programme — review package, 2026-10-10

3 Russian courses / 14 chapters / 43 lessons / 61 questions.
- 25 existing original ALLIM alphabet lessons, enriched with recognition checks.
- 10 original lessons on vowels, signs and first reading combinations.
- 8 original introductory tajwid lessons. This is NOT a full tajwid curriculum.

Audience: children 8–12 and teenagers 13–17. These are presentation tracks, not
an assessment of any named child. For a younger beginner, select one example
with a teacher and adapt duration. No child personal data is in this package.

Two deliverables:
1. index.html + preview.css + preview.js + catalog.js — LOCAL REVIEW ONLY.
   Works via an ordinary static server; exercises, hints, retry, age prompts,
   continue and browser-only progress. Not a replacement for the signed-in LMS.
2. courses.json + install.py — native draft-course data and create-only seed.
   Quiz progress after installation is managed by the existing academy.

Rebuild: python3 academy/youth_path/build.py
Validate: python3 academy/youth_path/test_package.py
Requires the existing academy/course_01_letters/content.py to rebuild.
No new runtime dependency, media copy or external tracking.

Install only after matching colleague-projects.json to the agreed app commits:
Copy install.py to allimquran/youth_curriculum/__init__.py and courses.json next
to it. Keep the source curriculum/preview under companion-workspace/academy.
Provide an EXISTING enabled test instructor with Course Creator/Moderator role.
Do not create or email real student accounts during validation.

Dry run on the agreed isolated test site:
bench --site allimquran.localhost execute allimquran.youth_curriculum.execute --kwargs '{"instructor":"<existing-test-instructor>"}'
Apply on that site:
bench --site allimquran.localhost execute allimquran.youth_curriculum.execute --kwargs '{"instructor":"<existing-test-instructor>","apply":true}'
Repeat dry-run: expect existing=164, create=0. The enclosing command owns commit.

164 documents: 3 courses, 14 chapters, 43 lessons, 43 quizzes, 61 questions.
All courses remain unpublished; certification and payment are disabled.
The importer checks schema, roles and ordinary permissions, refuses title/marker
collisions, protects published/edited records and aborts partial existing seeds.
Any apply error rolls back to a savepoint. No automatic update or deletion.
If ALLIM-C01 already exists, reconcile that draft explicitly before installation;
do not rename, delete or replace it automatically.

Teacher review before public release:
Check all Arabic examples, Quran citations in the retained alphabet course,
pronunciation progression and prerequisites. Muallim Awwal/Sani are discussed
accurately in research/sources.json; this is an original digital adaptation,
not a verified reproduction of an author's edition. Written checks do not
certify pronunciation, tajwid, memorization or ijazah. Teacher notes distinguish
recognition, rule application and oral performance.

Remaining deployment gates:
The agreed colleague-projects.json is missing; no local database installation,
migration, native student quiz submission or authenticated course access was
run. Review the instructor, existing drafts, private-file permissions and schema
on the agreed site before publishing. Video infrastructure remains separate;
see research/video-review.txt. No production mutation or independent deployment.
