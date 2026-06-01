"""Weather via Open-Meteo (no API key)."""
from __future__ import annotations
import asyncio
import json
import urllib.request

from google_client import load_config

_CODES = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "rime fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
    81: "rain showers", 82: "violent rain showers", 95: "thunderstorm",
}


def _sync_weather() -> str:
    w = load_config()["weather"]
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={w['latitude']}&longitude={w['longitude']}"
        "&current=temperature_2m,weather_code,wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,weather_code"
        "&timezone=auto&forecast_days=1"
    )
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    cur = data.get("current", {})
    daily = data.get("daily", {})
    label = w.get("label", "your location")
    cond = _CODES.get(cur.get("weather_code"), "unknown")
    t = cur.get("temperature_2m")
    tmax = (daily.get("temperature_2m_max") or [None])[0]
    tmin = (daily.get("temperature_2m_min") or [None])[0]
    return (f"{label}: currently {t}°C, {cond}. "
            f"Today {tmin}°C to {tmax}°C.")


async def get_weather() -> str:
    return await asyncio.to_thread(_sync_weather)
