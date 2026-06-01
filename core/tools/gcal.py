"""Google Calendar read-only: today's events."""
from __future__ import annotations
import asyncio
import datetime as dt

from google_client import service, with_retries


def _sync_today() -> str:
    svc = service("calendar", "v3")
    now = dt.datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(days=1)
    resp = svc.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    items = resp.get("items", [])
    if not items:
        return "No events on the calendar today."
    lines = []
    for ev in items:
        s = ev.get("start", {})
        when = s.get("dateTime", s.get("date", ""))
        # Trim ISO to HH:MM when it's a timed event.
        if "T" in when:
            when = when[11:16]
        title = ev.get("summary", "(untitled)")
        loc = ev.get("location", "")
        lines.append(f"- {when} {title}" + (f" @ {loc}" if loc else ""))
    return f"{len(lines)} event(s) today:\n" + "\n".join(lines)


async def get_calendar_today() -> str:
    return await asyncio.to_thread(with_retries, _sync_today)
