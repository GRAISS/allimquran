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
