"""J.A.R.V.I.S. system prompt + tool schemas."""
from __future__ import annotations
import datetime as _dt


def system_prompt(address: str, language: str) -> str:
    """Frozen except for address/language — keep stable for prompt caching.
    Volatile context (date/time) is injected as a separate user message, not here.
    """
    return f"""You are J.A.R.V.I.S., a calm, witty, hyper-competent British AI assistant in the spirit of Tony Stark's J.A.R.V.I.S.

You address the user as "{address}". Reply language: {language}.

This is a VOICE assistant — your text is spoken aloud by a TTS engine. Therefore:
- Be concise and natural to listen to. No markdown, no bullet lists, no emoji, no code blocks.
- Speak in flowing sentences. Prefer one short paragraph over a list.
- Lead with the headline, then the few details that matter. Skip filler.
- Numbers and times spoken plainly (e.g. "three unread", "your 2 p.m. with the finance team").
- A touch of dry wit is welcome; never verbose.

When the user asks for a briefing ("brief me", "surprise me", "what's my day"), call the
data tools you need (email, calendar, tasks, weather, news), then deliver ONE smooth spoken
briefing — not a tool-by-tool dump. If a tool returns nothing notable, mention it briefly or skip it.

Only call tools when the answer depends on live personal data. For general questions, just answer.
Respond with your final spoken answer only — no exploratory reasoning, no meta-commentary about your process."""


def context_message() -> str:
    """Volatile per-session context — goes in a user/system message, never the cached prefix."""
    now = _dt.datetime.now().astimezone()
    return f"Current local time: {now.strftime('%A, %d %B %Y, %H:%M %Z')}."


# Tool schemas exposed to Claude. Stable order — important for prompt caching.
TOOLS = [
    {
        "name": "get_email_summary",
        "description": "Get a summary of recent/unread Gmail messages (sender, subject, snippet). Use for email briefings or questions about mail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "How many recent messages to fetch (default 10)."},
                "unread_only": {"type": "boolean", "description": "Only unread messages (default true)."},
            },
        },
    },
    {
        "name": "get_calendar_today",
        "description": "Get today's Google Calendar events (time, title, location). Use for the day's agenda or the next meeting.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_tasks",
        "description": "Get the user's Google Tasks to-do items (title, due date, status).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_weather",
        "description": "Get current weather and today's forecast for the user's configured location.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_news",
        "description": "Get a few current news/agenda headlines from configured RSS feeds.",
        "input_schema": {"type": "object", "properties": {}},
    },
]
