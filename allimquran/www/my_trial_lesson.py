import frappe

from allimquran.trial_text import COPY

no_cache = 1
sitemap = 0


def get_context(context):
    from allimquran.review_portal import private_headers
    private_headers()
    lang = frappe.form_dict.get("lang") or frappe.local.lang or "en"
    context.trial_lang = lang if lang in COPY else "en"
    context.trial_copy = COPY[context.trial_lang]
    context.no_cache = 1
