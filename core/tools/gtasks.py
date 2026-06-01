"""Google Tasks read-only: open to-do items."""
from __future__ import annotations
import asyncio

from google_client import service, with_retries


def _sync_tasks() -> str:
    svc = service("tasks", "v1")
    lists = svc.tasklists().list(maxResults=10).execute().get("items", [])
    out = []
    for tl in lists:
        resp = svc.tasks().list(
            tasklist=tl["id"], showCompleted=False, maxResults=50
        ).execute()
        for t in resp.get("items", []):
            if t.get("status") == "completed":
                continue
            title = t.get("title", "").strip()
            if not title:
                continue
            due = t.get("due", "")
            due = f" (due {due[:10]})" if due else ""
            out.append(f"- {title}{due}")
    if not out:
        return "No open tasks."
    return f"{len(out)} open task(s):\n" + "\n".join(out)


async def get_tasks() -> str:
    return await asyncio.to_thread(with_retries, _sync_tasks)
