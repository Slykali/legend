"""Weather, news and the daily briefing."""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET

from ..agent import Agent
from ..scheduler import describe_due
from ..tools import Tool, build_tool, tool
from .web import http_get

WMO = {0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog",
       48: "freezing fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
       61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
       71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains", 80: "light showers",
       81: "showers", 82: "violent showers", 85: "snow showers", 86: "heavy snow showers",
       95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail"}


class WeatherAgent(Agent):
    name = "weather"
    title = "Weather"
    description = "Current weather and 3-day forecast for any city (free Open-Meteo service)."
    instructions = "Report weather naturally and briefly; mention anything the user should prepare for."

    @tool
    def get_weather(self, location: str = "") -> dict | str:
        """Get current conditions and a 3-day forecast.

        Args:
            location: City name, e.g. 'Paris' or 'Austin'. Empty uses the configured default.
        """
        location = location or self.ctx.config.get("weather.default_location")
        if not location:
            return "No location given and no weather.default_location configured. Ask the user for a city."
        name = location.split(",")[0].strip()
        geo = json.loads(http_get("https://geocoding-api.open-meteo.com/v1/search?"
                                  + urllib.parse.urlencode({"name": name, "count": 1}))[0])
        if not geo.get("results"):
            return f"Could not find a place called '{location}'."
        place = geo["results"][0]
        imperial = self.ctx.config.get("weather.units") == "imperial"
        params = {
            "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 3,
        }
        if imperial:
            params.update(temperature_unit="fahrenheit", wind_speed_unit="mph")
        data = json.loads(http_get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params))[0])
        cur, daily = data["current"], data["daily"]
        t, w = ("°F", "mph") if imperial else ("°C", "km/h")
        return {
            "place": f"{place['name']}, {place.get('country', '')}",
            "now": f"{cur['temperature_2m']}{t} (feels {cur['apparent_temperature']}{t}), "
                   f"{WMO.get(cur['weather_code'], 'unknown')}, humidity {cur['relative_humidity_2m']}%, "
                   f"wind {cur['wind_speed_10m']} {w}",
            "forecast": [
                f"{daily['time'][i]}: {WMO.get(daily['weather_code'][i], '?')}, "
                f"{daily['temperature_2m_min'][i]}–{daily['temperature_2m_max'][i]}{t}, "
                f"rain chance {daily['precipitation_probability_max'][i]}%"
                for i in range(len(daily["time"]))
            ],
        }


def parse_feed(xml_text: str, limit: int) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        # Element truthiness depends on children, so compare with None explicitly.
        get = lambda name: next((c for c in el if c.tag.split("}")[-1] == name), None)  # noqa: E731
        title = get("title")
        link = get("link")
        date = next((d for d in map(get, ("pubDate", "updated", "published")) if d is not None), None)
        href = (link.get("href") or link.text) if link is not None else ""
        items.append({"title": re.sub(r"\s+", " ", (title.text or "") if title is not None else "").strip(),
                      "link": (href or "").strip(),
                      "date": (date.text or "").strip()[:25] if date is not None else ""})
        if len(items) >= limit:
            break
    return items


class NewsAgent(Agent):
    name = "news"
    title = "News"
    description = "Latest headlines by category (world, tech, science...) or on any topic."
    instructions = "Summarise headlines crisply; group related stories; offer links on request."

    @tool
    def get_headlines(self, topic: str = "world", max_items: int = 8) -> list[dict] | str:
        """Fetch current headlines.

        Args:
            topic: A configured feed (world, tech, science, hackernews) or any search topic.
            max_items: Number of headlines.
        """
        feeds = self.ctx.config.get("news.feeds", {})
        url = feeds.get(topic.lower().strip())
        if not url:
            url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
                {"q": topic, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        return parse_feed(http_get(url)[0], int(max_items)) or f"No headlines found for '{topic}'."

    @tool
    def list_news_feeds(self) -> dict:
        """List configured news feeds."""
        return self.ctx.config.get("news.feeds", {})


class BriefingAgent(Agent):
    name = "briefing"
    title = "Briefing"
    description = ("Daily briefing: date, weather, to-dos, upcoming reminders and top headlines "
                   "in one summary. Use for 'good morning', 'brief me', 'what's my day like'.")
    instructions = ("Prepare a short, upbeat spoken-style briefing. Gather weather, to-dos, "
                    "reminders and a few headlines, then summarise in under 150 words.")
    max_steps = 6

    def get_tools(self) -> list[Tool]:
        weather = WeatherAgent(self.ctx)
        news = NewsAgent(self.ctx)
        return [build_tool(weather.get_weather), build_tool(news.get_headlines),
                *super().get_tools()]

    @tool
    def agenda(self) -> dict:
        """Get open to-dos and upcoming reminders."""
        rems = [f"{describe_due(r['due'])}: {r['message']}" for r in self.ctx.memory.pending_reminders()]
        todos = [f"#{t['id']} {t['text']}" + (f" (due {t['due']})" if t["due"] else "")
                 for t in self.ctx.memory.list_todos()]
        return {"today": f"{dt.date.today():%A %d %B %Y}", "todos": todos or ["none"],
                "reminders": rems or ["none"]}
