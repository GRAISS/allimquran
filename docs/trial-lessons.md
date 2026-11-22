# Trial lessons

A request now has a coordinator and follow-up deadline, a teacher appointment, and a recorded outcome. A learning-group link alone no longer means a trial has been scheduled.

## Daily handling

1. Open **ALLIM Trial Settings**. Select an active coordinator who already has permission to manage trial requests. Set the first-contact interval (default 24 hours). Confirm the outgoing mailbox and its reply handling, then enable learner/teacher email. Staff notification email follows their existing notification preferences.
2. New requests enter **New**. The coordinator gets an internal notification; without a default coordinator, active System Managers are notified and the request remains in **Unassigned requests**.
3. Use **Contacted** to record the next follow-up deadline. Use **Schedule trial lesson** to set the coordinator, teacher, future start, learner time zone, duration and HTTPS meeting link. Start/completion/follow-up fields use the site's time zone; messages display the scheduled time in the learner's selected IANA time zone.
4. The learner receives the appointment and reminders in the 24-hour and 1-hour windows. The teacher receives appointment/reminder email. Jobs run every five minutes, so reminders are not guaranteed to the exact minute. Rescheduling invalidates notices not yet queued. Already queued/delivered email cannot be recalled; the latest appointment on the private page is authoritative.
5. The coordinator records the teacher's assessment using **Record lesson result**: actual completion time, what was assessed, recommended learning plan, learner's next step, and a follow-up deadline. The teacher's existing permissions are not expanded. Teachers without request-management rights return their assessment to the coordinator.
6. **No Show** requires a past lesson, reason and follow-up; **Reschedule** requires a reason and follow-up. **Closed** requires an internal reason. A completed lesson stays actionable until confirmed enrollment or closure.
7. **Confirm enrollment** checks a real existing group enrollment on the server. This change does not create groups, enroll students, charge money, or modify the learning application.

## Learner page

`/my-trial-lesson?lang=ru` (also `en` and `ar`) shows only requests bound to the signed-in originating applicant. The Academy and all three trial forms link to it. It shows appointment details, join link, result and next step. Internal notes and teacher account identifiers are excluded. Guest applicants receive consented email; an email-only match never grants account access.

Existing requests are linked only when their original authenticated creator matches their contact email. Guest/admin-created requests are not silently linked to another account. No existing consent, completion, schedule or enrollment is invented.

## Installation and acceptance

The owner's approved PR target is `main` at `24a9b74403ee8052f325dba3511d5442fd4d00c6`, with PR #7 preserved. This change is stacked on PR #7 (`a2ad3807988455f59c49dee3fb8e537788a9112f`). Review/merge the prerequisites first; then the target diff reduces to the trial changes. Do not deploy this branch ahead of the agreed prerequisite review.

Use the agreed environment manifest; do not install an arbitrary current environment. In the isolated test bench:

```sh
bench --site allimquran.localhost migrate
bench --site allimquran.localhost execute allimquran.trial_setup.install
bench --site allimquran.localhost enable-scheduler
```

The migration adds application-owned schemas and the scheduler hook, preserves existing fields and records, and disables only the known old `ALLIM Trial Request Workflow` client script. Unknown modified scripts cause the preflight to stop for reconciliation. Run install twice to verify idempotence. Standard source drift guards remain active. The deployment operator should restart the existing workers/scheduler using the environment's normal procedure and clear the website cache.

Use only synthetic users and a local mail catcher; set the site to mute real email during validation, including staff notification email. Configure **ALLIM Trial Settings** in the UI. No new credentials or private dependencies are bundled.

Acceptance: anonymous and authenticated form submission; new internal alert; valid/invalid scheduling; correct time conversion; two reminder windows; reschedule before delivery; withdrawn consent; SMTP failure/retry; result receipt; no-show and overdue follow-up; enrollment rejection/confirmation; another learner cannot read the first learner's records. Inspect **ALLIM Trial Notice** and the mail queue. `Queued` means submitted to the mail queue, not delivered. `Notified` means an internal notification was created, not read. Verify actual delivery separately with the test mailbox.

## Validation of this review package

- 26 focused lifecycle/delivery/privacy tests; 3 existing contact tests; 9 setup tests.
- Source-manifest regression checks (11 passed, one existing optional export-snapshot check skipped), schema uniqueness/field order, Python parsing and JavaScript syntax. Total: 49 passed, one skipped.
- Local fixture preview: desktop RU; mobile 390px RU result and AR/RTL; EN guest, empty and error states; retry action; no horizontal overflow in AR.
- Browser preview uses the actual template, CSS and JavaScript with a minimal test layout and synthetic API. It does not prove the installed site or mail integration.
- Full database migration, installed Desk actions, real mail delivery, scheduler execution and production behavior still require the agreed environment. No production request was edited, and no real lesson or notification was claimed to have occurred.

Rollback requires the prior application source and the preserved legacy script state. Retain the new result/outbox data; do not drop tables or delete learner records. Pending jobs should be paused by the deployment operator before rollback.


## Owner designation (22 November 2026)

The product owner has selected himself as the interim coordinator for new trial requests and overdue follow-ups. Choose his existing ALLIM account in **ALLIM Trial Settings**; do not create another account or grant new roles. His account identifier belongs in the site's configuration, not this public repository.

After migration, an operator may apply the same configuration reproducibly with the non-public setup command:

```sh
bench --site allimquran.localhost execute allimquran.trial_setup.configure --kwargs '{"coordinator":"OWNER_ACCOUNT_ID","response_hours":24,"assign_existing":true}'
```

Replace the placeholder with the owner's verified existing account. This sets the default for future requests and assigns only existing open requests that have no coordinator. It preserves other staff assignments, consent, schedules, learner binding and results. The default initial follow-up deadline is 24 hours after the request's creation, so old requests remain visibly overdue. No learner/teacher email is enabled by this command. Staff receive in-app alerts; email follows their configured notification preferences and the outgoing-mail setup.

New requests and overdue work have distinct notification titles. The previously linked live request was assigned to the owner through the existing assignment UI on 22 November. The new default and scheduled overdue processing remain pending deployment of this PR; configuring the live defaults before the new settings exist is not claimed.
