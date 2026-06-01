"""News/agenda headlines from configured RSS feeds (no API key)."""
from __future__ import annotations
import asyncio
import urllib.request
import xml.etree.ElementTree as ET

from google_client import load_config


def _sync_news() -> str:
    n = load_config()["news"]
    feeds = n.get("feeds", [])
    max_items = int(n.get("max_items", 5))
    titles: list[str] = []
    for url in feeds:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                root = ET.fromstring(r.read())
            for item in root.iter("item"):
                t = item.findtext("title")
                if t:
                    titles.append(t.strip())
                if len(titles) >= max_items:
                    break
        except Exception:
            continue
        if len(titles) >= max_items:
            break
    if not titles:
        return "No headlines available."
    return "Headlines:\n" + "\n".join(f"- {t}" for t in titles[:max_items])


async def get_news() -> str:
    return await asyncio.to_thread(_sync_news)
