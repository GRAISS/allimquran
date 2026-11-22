"""Idempotent migration of trial handling; does not send messages or infer outcomes."""

import hashlib
import json
from pathlib import Path

import frappe


def preflight():
    name = "ALLIM Trial Request Workflow"
    known = json.loads((Path(__file__).parent / "trial_legacy_hashes.json").read_text())
    if frappe.db.exists("Client Script", name):
        script = frappe.get_doc("Client Script", name)
        if script.enabled:
            digest = hashlib.sha256((script.script or "").strip().encode()).hexdigest()
            if digest not in known:
                frappe.throw("ALLIM trial script has local changes. Reconcile it before enabling the new workflow.")
    return name


def install():
    from allimquran.trial_lifecycle import REQUEST
    name = preflight()
    if frappe.db.exists("Client Script", name):
        frappe.db.set_value("Client Script", name, "enabled", 0)
    # Original authenticated authorship is evidence; an email-only match is not.
    for row in frappe.get_all(REQUEST, filters={"trial_learner": ["is", "not set"]}, fields=["name", "owner", "email"]):
        if row.owner and row.owner not in ("Guest", "Administrator"):
            email = frappe.db.get_value("User", row.owner, "email")
            if email and email.casefold() == (row.email or "").casefold():
                frappe.db.set_value(REQUEST, row.name, "trial_learner", row.owner, update_modified=False)
    frappe.clear_cache(doctype=REQUEST)


def configure(coordinator, response_hours=24, assign_existing=False):
    """Operator-only setup after migration; recipient identifiers stay out of source."""
    from frappe.utils import add_to_date, cint
    from allimquran.trial_lifecycle import REQUEST, SETTINGS

    if not frappe.db.get_value("User", coordinator, "enabled"):
        frappe.throw("Choose an enabled trial coordinator.")
    if not frappe.has_permission(REQUEST, "write", user=coordinator):
        frappe.throw("The coordinator needs permission to manage trial requests.")
    hours = cint(response_hours)
    if not 1 <= hours <= 168:
        frappe.throw("The first-contact deadline must be between 1 and 168 hours.")
    config = frappe.get_single(SETTINGS)
    config.coordinator = coordinator
    config.response_hours = hours
    config.save(ignore_permissions=True)
    updated = []
    if cint(assign_existing):
        names = frappe.get_all(REQUEST, filters={"trial_coordinator": ["is", "not set"],
                               "status": ["not in", ["Closed", "Enrolled"]]}, pluck="name")
        for name in names:
            doc = frappe.get_doc(REQUEST, name, for_update=True)
            if doc.trial_coordinator or doc.status in ("Closed", "Enrolled"):
                continue
            doc.trial_coordinator = coordinator
            doc.trial_follow_up = doc.trial_follow_up or add_to_date(doc.creation, hours=hours)
            doc.save(ignore_permissions=True)
            updated.append(name)
    return {"coordinator": coordinator, "response_hours": hours, "assigned_existing": updated}
