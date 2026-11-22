"""Application-owned trial handling. Outgoing messages use the normal mail queue."""

import hashlib
from html import escape
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, get_system_timezone, get_url, now_datetime

from allimquran.trial_rules import RESULT_FIELDS, SCHEDULE_FIELDS, check

REQUEST = "ALLIM Trial Lesson Request"
NOTICE = "ALLIM Trial Notice"
SETTINGS = "ALLIM Trial Settings"
ADMIN_FIELDS = (*SCHEDULE_FIELDS, *RESULT_FIELDS, "trial_coordinator", "trial_follow_up",
                "trial_reason", "trial_learner", "trial_version")


def settings():
    return frappe.get_single(SETTINGS)


def validate(doc):
    previous = doc.get_doc_before_save()
    config = settings()
    if doc.is_new():
        if not frappe.has_permission(REQUEST, "write"):
            for field in ADMIN_FIELDS:
                doc.set(field, None)
        doc.status = "New"
        doc.trial_learner = frappe.session.user if frappe.session.user != "Guest" else None
        doc.trial_coordinator = doc.get("trial_coordinator") or config.coordinator
        doc.trial_follow_up = add_to_date(now_datetime(), hours=cint(config.response_hours) or 24)
    # Never infer portal ownership from a visitor-supplied email or the legacy student_user field.
    elif previous and doc.trial_learner != previous.trial_learner:
        frappe.throw(_("The trial learner account cannot be changed."))
    for field in ("trial_coordinator", "trial_teacher"):
        user = doc.get(field)
        if user and not frappe.db.get_value("User", user, "enabled"):
            frappe.throw(_("Choose an enabled user."))
    if doc.trial_coordinator and not frappe.has_permission(REQUEST, "write", user=doc.trial_coordinator):
        frappe.throw(_("The coordinator needs permission to manage trial requests."))
    if doc.get("trial_timezone"):
        try:
            ZoneInfo(doc.trial_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            frappe.throw(_("Use a valid time zone, for example Europe/Moscow."))
    enrolled = False
    if doc.status == "Enrolled" and (not previous or previous.status != "Enrolled"):
        enrolled = bool(doc.get("student_user") and doc.get("learning_group") and frappe.db.exists(
            "LMS Batch Enrollment", {"member": doc.student_user, "batch": doc.learning_group}))
    error = check(doc.as_dict(), previous.as_dict() if previous else None, now_datetime(), enrolled)
    if error:
        frappe.throw(_(error))
    changed = not previous or any(doc.get(f) != previous.get(f) for f in (*SCHEDULE_FIELDS, *RESULT_FIELDS, "email", "consent"))
    if changed or (previous and doc.status != previous.status):
        doc.trial_version = cint(previous.trial_version if previous else 0) + 1
    else:
        doc.trial_version = cint(previous.trial_version)


def recipients(doc):
    if (doc.trial_coordinator and frappe.db.get_value("User", doc.trial_coordinator, "enabled")
            and frappe.has_permission(REQUEST, "read", user=doc.trial_coordinator)):
        return [doc.trial_coordinator]
    candidates = set(frappe.get_all("Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent"))
    active = sorted(user for user in candidates if frappe.db.get_value("User", user, "enabled"))
    return active or ["Administrator"]


def enqueue_notice(doc, kind, audience, recipient, suffix=""):
    key = hashlib.sha256(f"{doc.name}|{doc.trial_version}|{kind}|{audience}|{recipient}|{suffix}".encode()).hexdigest()
    if not recipient or frappe.db.exists(NOTICE, key):
        return
    frappe.get_doc({"doctype": NOTICE, "name": key, "trial_request": doc.name,
                    "kind": kind, "audience": audience, "recipient": recipient,
                    "version": doc.trial_version, "state": "Pending"}).insert(ignore_permissions=True, set_name=key)


def on_update(doc):
    previous = doc.get_doc_before_save()
    changed = not previous or doc.status != previous.status or doc.trial_version != previous.trial_version
    assigned = previous and doc.trial_coordinator != previous.trial_coordinator
    if changed or assigned:
        for user in recipients(doc):
            enqueue_notice(doc, "Action", "Staff", user, doc.trial_coordinator or "unassigned")
    if not previous:
        enqueue_notice(doc, "Received", "Learner", doc.email)
    elif changed and doc.status in ("Scheduled", "Completed", "Reschedule", "No Show", "Closed", "Enrolled"):
        enqueue_notice(doc, doc.status, "Learner", doc.email)
    if changed and doc.status == "Scheduled" and doc.trial_teacher:
        enqueue_notice(doc, "Scheduled", "Teacher", doc.trial_teacher)


def local_start(doc):
    if not doc.trial_start:
        return ""
    dt = get_datetime(doc.trial_start).replace(tzinfo=ZoneInfo(get_system_timezone()))
    zone = doc.trial_timezone or get_system_timezone()
    return dt.astimezone(ZoneInfo(zone)).strftime("%d.%m.%Y %H:%M") + " · " + zone


def message(doc, notice):
    lang = doc.language if doc.language in ("en", "ru", "ar") else "en"
    from allimquran.trial_text import COPY
    text = COPY[lang]
    title = text.get(notice.kind, text["Action"])
    body = [f'<h2>{escape(title)}</h2>', f'<p>{escape(doc.name)}</p>']
    if notice.audience == "Staff":
        link = get_url("/desk/allim-trial-lesson-request/" + quote(doc.name, safe=""))
        body += [f'<p>{escape(text["manage"])}</p>', f'<p><a href="{escape(link, quote=True)}">ALLIM</a></p>']
    else:
        if doc.status == "Scheduled":
            body += [f'<p>{escape(local_start(doc))} · {cint(doc.trial_duration)} {escape(text["minutes"])}</p>',
                     f'<p><a href="{escape(doc.trial_meeting_url, quote=True)}">{escape(text["join"])}</a></p>']
        if doc.status in ("Completed", "Enrolled") and notice.audience == "Learner":
            for label, field in (("result", "trial_result"), ("recommendation", "trial_recommendation"), ("next", "trial_next_step")):
                body += [f'<p><b>{escape(text[label])}</b><br>{escape(doc.get(field) or "")}</p>']
        body += [f'<p>{escape(text["reply"])}</p>']
        if doc.trial_learner and notice.audience == "Learner":
            body += [f'<p><a href="{escape(get_url("/my-trial-lesson?lang=" + lang), quote=True)}">{escape(text["portal"])}</a></p>']
    return title, f'<div lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}">' + "".join(body) + "</div>"


def deliver(name):
    # Lock request then notice consistently; a reschedule cannot race delivery selection.
    ref = frappe.db.get_value(NOTICE, name, "trial_request")
    doc = frappe.get_doc(REQUEST, ref, for_update=True)
    notice = frappe.get_doc(NOTICE, name, for_update=True)
    if notice.state != "Pending":
        return
    if cint(notice.version) != cint(doc.trial_version):
        notice.db_set("state", "Superseded", update_modified=False)
        return
    config = settings()
    if notice.audience == "Learner" and (not doc.consent or notice.recipient != doc.email):
        notice.db_set("state", "Suppressed", update_modified=False)
        return
    if notice.audience != "Learner" and not frappe.db.get_value("User", notice.recipient, "enabled"):
        notice.db_set("state", "Suppressed", update_modified=False)
        return
    if notice.audience == "Staff" and notice.recipient not in recipients(doc):
        notice.db_set("state", "Superseded", update_modified=False)
        return
    if notice.audience == "Teacher" and notice.recipient != doc.trial_teacher:
        notice.db_set("state", "Superseded", update_modified=False)
        return
    if notice.kind == "Reminder" and (doc.status != "Scheduled" or get_datetime(doc.trial_start) <= now_datetime()):
        notice.db_set("state", "Superseded", update_modified=False)
        return
    title, body = message(doc, notice)
    if notice.audience == "Staff":
        # Standard notification preferences control staff mail, even if learner mail is disabled.
        frappe.get_doc({"doctype": "Notification Log", "type": "Alert", "subject": title,
                        "for_user": notice.recipient, "document_type": REQUEST,
                        "document_name": doc.name, "email_content": body}).insert(ignore_permissions=True)
        notice.db_set("state", "Notified", update_modified=False)
    else:
        if not config.email_enabled:
            return
        email = notice.recipient if notice.audience == "Learner" else frappe.db.get_value("User", notice.recipient, "email")
        if not email:
            notice.db_set("state", "Suppressed", update_modified=False)
            return
        frappe.sendmail(recipients=[email], subject=title, message=body, delayed=True,
                        reference_doctype=REQUEST, reference_name=doc.name)
        notice.db_set("state", "Queued", update_modified=False)


def tick():
    """Every five minutes; transactions isolate individual requests and delivery attempts."""
    now = now_datetime()
    for name in frappe.get_all(REQUEST, filters={"status": ["not in", ["Closed", "Enrolled"]]}, pluck="name"):
        try:
            doc = frappe.get_doc(REQUEST, name, for_update=True)
            if doc.status in ("Closed", "Enrolled"):
                frappe.db.commit()
                continue
            # Also picks up existing requests after installation, without fabricating consent/results.
            deadline = doc.trial_follow_up or doc.creation
            overdue = get_datetime(deadline) <= now
            if doc.status == "Scheduled":
                overdue = not doc.trial_start or get_datetime(doc.trial_start) <= now
                if doc.trial_start and now < get_datetime(doc.trial_start) <= add_to_date(now, hours=24):
                    window = "1h" if get_datetime(doc.trial_start) <= add_to_date(now, hours=1) else "24h"
                    enqueue_notice(doc, "Reminder", "Learner", doc.email, window)
                    enqueue_notice(doc, "Reminder", "Teacher", doc.trial_teacher, window)
            if overdue or not doc.trial_coordinator:
                for user in recipients(doc):
                    enqueue_notice(doc, "Action", "Staff", user, str(now.date()))
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title="ALLIM trial follow-up failed")
    notice_filters = {"state": "Pending"}
    if not settings().email_enabled:
        notice_filters["audience"] = "Staff"
    for name in frappe.get_all(NOTICE, filters=notice_filters, pluck="name", limit_page_length=200, order_by="modified asc"):
        try:
            deliver(name)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            # Move failed items to the back of the next batch without dropping the retry.
            frappe.db.set_value(NOTICE, name, "last_error", _("Delivery failed. Check the error log and outgoing mail configuration."))
            frappe.db.commit()
            frappe.log_error(title="ALLIM trial notice failed")


@frappe.whitelist(methods=["GET"])
def my_trials():
    from allimquran.review_portal import private_headers
    private_headers()
    user = frappe.session.user
    if user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
        frappe.throw(_("Sign in to view your trial lesson."), frappe.PermissionError)
    rows = frappe.get_all(REQUEST, filters={"trial_learner": user}, fields=["name", "status", "trial_start",
        "trial_timezone", "trial_duration", "trial_teacher", "trial_meeting_url", "trial_completed_at",
        "trial_result", "trial_recommendation", "trial_next_step", "trial_reason"], order_by="creation desc", limit_page_length=20)
    for row in rows:
        row["start_label"] = local_start(row)
        row["teacher_name"] = frappe.db.get_value("User", row.trial_teacher, "full_name") if row.trial_teacher else ""
        row.pop("trial_teacher", None)
        if row.status != "Scheduled":
            row["trial_meeting_url"] = ""
        if row.status not in ("Completed", "Enrolled", "Closed"):
            for field in RESULT_FIELDS:
                row[field] = ""
        # Operational reasons may contain private notes; never return them to the learner.
        row.pop("trial_reason", None)
    return rows
