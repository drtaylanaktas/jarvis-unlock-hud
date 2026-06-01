"""Gmail read-only summary tool."""
from __future__ import annotations
import asyncio
import base64

from google_client import service, with_retries


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _sync_summary(max_results: int, unread_only: bool) -> str:
    svc = service("gmail", "v1")
    q = "is:unread" if unread_only else ""
    resp = svc.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    msgs = resp.get("messages", [])
    if not msgs:
        return "No unread messages." if unread_only else "No recent messages."
    lines = []
    for m in msgs:
        full = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = full.get("payload", {}).get("headers", [])
        sender = _header(headers, "From")
        subject = _header(headers, "Subject") or "(no subject)"
        snippet = full.get("snippet", "")[:160]
        lines.append(f"- From {sender}: {subject} — {snippet}")
    return f"{len(lines)} message(s):\n" + "\n".join(lines)


async def get_email_summary(max_results: int = 10, unread_only: bool = True) -> str:
    return await asyncio.to_thread(with_retries, _sync_summary, int(max_results), bool(unread_only))
