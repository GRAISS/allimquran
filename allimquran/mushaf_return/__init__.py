"""Narrow, idempotent learn-page patch. Importing this module never writes data."""
import json
import re
from pathlib import Path


def replace_block(text, start, end, block, anchor=None):
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError("Ambiguous patch markers")
        left, right = text.index(start), text.index(end) + len(end)
        if right <= left:
            raise ValueError("Invalid patch marker order")
        return text[:left] + block + text[right:]
    if anchor is None:
        return text.rstrip() + "\n\n" + block + "\n"
    if text.count(anchor) != 1:
        raise ValueError("Expected one anchor: " + anchor)
    return text.replace(anchor, block + "\n" + anchor, 1)


def prepare(html, css, javascript):
    payload = json.loads(Path(__file__).with_name("payload.json").read_text())
    html_start = "<!-- ALLIM_MUSHAF_MOBILE_EXIT_V1_START -->"
    if 'id="mushaf-exit"' in html and html_start not in html:
        raise ValueError("Unmanaged existing exit control; review required")
    html = replace_block(html, html_start, "<!-- ALLIM_MUSHAF_MOBILE_EXIT_V1_END -->",
                         payload["html"], '<div class="mushaf-toolbar">')
    css = replace_block(css, "/* ALLIM_MUSHAF_MOBILE_EXIT_V1_START */",
                        "/* ALLIM_MUSHAF_MOBILE_EXIT_V1_END */", payload["css"])
    for name in ("clearAutoAdvance", "stopRecognitionImmediately", "setMushafMode",
                 "stopVerseAudio", "setStudioMode", "selectReaderMode", "setMeaningVisibility"):
        if not re.search(r"function\s+" + name + r"\s*\(", javascript):
            raise ValueError("Missing required reader function: " + name)
    start, end = "/* ALLIM_MUSHAF_RETURN_TRANSLATIONS_START */", "/* ALLIM_MUSHAF_RETURN_TRANSLATIONS_END */"
    javascript = replace_block(javascript, start, end,
                               start + "\n" + payload["translations"] + "\n" + end,
                               "var reciters = [")
    function = re.compile(r"function exitMushafToReading\(restoreFocus\) \{.*?\n  \}", re.S)
    if "function exitMushafToReading" in javascript:
        if len(function.findall(javascript)) != 1:
            raise ValueError("Unrecognized exit function; review required")
        javascript = function.sub(lambda _: payload["function"], javascript, count=1)
    else:
        anchor = "function updateMushafFontUi() {"
        if javascript.count(anchor) != 1:
            raise ValueError("Missing reader function anchor")
        javascript = javascript.replace(anchor, payload["function"] + "\n\n  " + anchor, 1)
    listener = payload["listener"]
    if listener not in javascript:
        if 'getElementById("mushaf-exit")' in javascript:
            raise ValueError("Unrecognized exit listener; review required")
        anchor = 'document.getElementById("mushaf-prev-page").addEventListener'
        if javascript.count(anchor) != 1:
            raise ValueError("Missing reader listener anchor")
        javascript = javascript.replace(anchor, listener + "\n    " + anchor, 1)
    return html, css, javascript


def execute(apply=False):
    import frappe
    from frappe.utils import cint

    apply = bool(cint(apply))
    page = frappe.get_doc("Web Page", {"route": "learn"})
    fields = ("main_section_html", "css", "javascript")
    before = tuple(page.get(field) or "" for field in fields)
    after = prepare(*before)
    changed = [field for field, old, new in zip(fields, before, after) if old != new]
    if apply and changed:
        page.check_permission("write")
        for field, value in zip(fields, after):
            page.set(field, value)
        page.save()
        frappe.clear_cache()
    return {"route": "learn", "changed_fields": changed, "applied": bool(apply and changed)}
