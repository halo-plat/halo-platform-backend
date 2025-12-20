from __future__ import annotations

from datetime import datetime, timezone, timedelta
from urllib.parse import quote

def build_notion_calendar_show_event_url(
    account_email: str,
    ical_uid: str,
    start_utc: datetime,
    end_utc: datetime,
    title: str,
    ref: str = "com.halo.desktop"
) -> str:
    # Notion Calendar local API (cron://) deep-link. Dates must be ISO-8601 with Z.
    s = start_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    e = end_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return (
        "cron://showEvent?"
        f"accountEmail={quote(account_email)}"
        f"&iCalUID={quote(ical_uid)}"
        f"&startDate={quote(s)}"
        f"&endDate={quote(e)}"
        f"&title={quote(title)}"
        f"&ref={quote(ref)}"
    )


def build_demo_event(session_id: str) -> dict:
    now = datetime.now(timezone.utc)
    start = now + timedelta(minutes=2)
    end = start + timedelta(minutes=20)
    ical_uid = f"halo-{session_id}@halo.local"
    return {
        "start_utc": start,
        "end_utc": end,
        "ical_uid": ical_uid,
        "title": "Halo – Quick focus block",
    }
