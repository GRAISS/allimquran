"""Trial lifecycle rules, independent of storage and delivery."""

from datetime import datetime
from urllib.parse import urlsplit

TRANSITIONS = {
    "New": {"Contacted", "Scheduled", "Closed"},
    "Contacted": {"Scheduled", "Closed"},
    "Scheduled": {"Completed", "No Show", "Reschedule", "Closed"},
    "Reschedule": {"Contacted", "Scheduled", "Closed"},
    "No Show": {"Contacted", "Scheduled", "Closed"},
    "Completed": {"Enrolled", "Closed"},
    "Enrolled": set(), "Closed": set(),
}
SCHEDULE_FIELDS = ("trial_start", "trial_timezone", "trial_duration", "trial_teacher", "trial_meeting_url")
RESULT_FIELDS = ("trial_completed_at", "trial_result", "trial_recommendation", "trial_next_step")


def secure_url(value):
    try:
        url = urlsplit(value or "")
        return bool(url.scheme == "https" and url.hostname and not url.username and not url.password
                    and not any(ord(c) < 33 for c in value))
    except ValueError:
        return False


def check(current, previous, now, enrollment_exists=False):
    """Return a translatable error; existing legacy rows remain editable."""
    status = current.get("status") or "New"
    old = (previous or {}).get("status") or "New"
    changed = previous is None or status != old
    if status not in TRANSITIONS:
        return "Unknown trial status."
    if changed and status != old and status not in TRANSITIONS.get(old, set()):
        return "This trial status transition is not allowed."
    if previous is None and status != "New":
        return "A trial request must start as New."
    if previous is None and not current.get("consent"):
        return "Consent is required for a new trial request."
    if changed and status not in ("New", "Closed") and not current.get("trial_coordinator"):
        return "Choose a trial coordinator."
    schedule_changed = any(current.get(f) != (previous or {}).get(f) for f in SCHEDULE_FIELDS)
    if status == "Scheduled" and (changed or schedule_changed):
        if not all(current.get(f) for f in SCHEDULE_FIELDS):
            return "Set the teacher, date, time zone, duration and meeting link."
        if not secure_url(current.get("trial_meeting_url")):
            return "Use an HTTPS meeting link without embedded credentials."
        start = datetime.fromisoformat(str(current["trial_start"]))
        if start <= now:
            return "The trial must be scheduled in the future."
        if not 10 <= int(current["trial_duration"]) <= 180:
            return "Trial duration must be between 10 and 180 minutes."
    result_changed = any(current.get(f) != (previous or {}).get(f) for f in RESULT_FIELDS)
    if status in ("Completed", "Enrolled") and (changed or result_changed):
        if not all(current.get(f) for f in RESULT_FIELDS) or not current.get("trial_teacher"):
            return "Record the teacher, completion time, result, recommendation and next step."
        completed = datetime.fromisoformat(str(current["trial_completed_at"]))
        if completed > now or (current.get("trial_start") and completed < datetime.fromisoformat(str(current["trial_start"]))):
            return "Completion time must be after the lesson start and not in the future."
    if changed and status in ("No Show", "Reschedule", "Closed") and not current.get("trial_reason"):
        return "Record the reason for this status."
    if changed and status == "No Show" and (not current.get("trial_start") or datetime.fromisoformat(str(current["trial_start"])) > now):
        return "A future lesson cannot be marked as missed."
    if changed and status in ("Contacted", "Reschedule", "No Show", "Completed") and not current.get("trial_follow_up"):
        return "Set the next follow-up deadline."
    if changed and status == "Enrolled" and not enrollment_exists:
        return "Confirm the existing learning group enrollment before marking Enrolled."
    return None
