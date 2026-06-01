"""Tool dispatch table mapping Claude tool names -> async callables."""
from .gmail import get_email_summary
from .gcal import get_calendar_today
from .gtasks import get_tasks
from .weather import get_weather
from .news import get_news

DISPATCH = {
    "get_email_summary": get_email_summary,
    "get_calendar_today": get_calendar_today,
    "get_tasks": get_tasks,
    "get_weather": get_weather,
    "get_news": get_news,
}
