"""Background reminder/timer service and natural time parsing."""
from __future__ import annotations

import datetime as dt
import re
import threading
from typing import Callable

from . import platform_utils

UNITS = {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
         "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
         "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
         "d": 86400, "day": 86400, "days": 86400, "week": 604800, "weeks": 604800}
WORD_NUMS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "ten": 10,
             "fifteen": 15, "twenty": 20, "thirty": 30, "forty-five": 45, "half an": 0.5}


def _clock(text: str) -> tuple[int, int] | None:
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not m or (m.group(2) is None and m.group(3) is None):
        return None
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    if m.group(3) == "pm" and hour < 12:
        hour += 12
    if m.group(3) == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return hour, minute


def parse_when(text: str, now: dt.datetime | None = None) -> dt.datetime:
    """Parse "in 10 minutes", "at 5pm", "tomorrow 9:30", "2026-01-05 14:00"."""
    now = now or dt.datetime.now()
    t = text.strip().lower().replace("half an hour", "30 minutes")

    for word, num in WORD_NUMS.items():
        t = re.sub(rf"\b{word}\b(?=\s+(sec|min|hour|day|week))", str(num), t)
    rel = re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]+)", t.removeprefix("in ").strip())
    if t.startswith("in ") or (rel and all(u in UNITS for _, u in rel) and not _clock(t)):
        seconds = sum(float(n) * UNITS[u] for n, u in rel if u in UNITS)
        if seconds > 0:
            return now + dt.timedelta(seconds=seconds)

    try:
        return dt.datetime.fromisoformat(text.strip().replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    m = re.search(r"(\d{4}-\d{2}-\d{2})", t)
    if m:
        day = dt.date.fromisoformat(m.group(1))
        hm = _clock(t[m.end():]) or (9, 0)
        return dt.datetime.combine(day, dt.time(*hm))

    day = now.date()
    if "tomorrow" in t:
        day += dt.timedelta(days=1)
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, name in enumerate(weekdays):
        if name in t:
            ahead = (i - now.weekday()) % 7 or 7
            day = now.date() + dt.timedelta(days=ahead)
    hm = _clock(t)
    if hm is None:
        if "noon" in t:
            hm = (12, 0)
        elif "tonight" in t or "evening" in t:
            hm = (20, 0)
        elif "morning" in t:
            hm = (9, 0)
        elif day != now.date():
            hm = (9, 0)
        else:
            raise ValueError(f"Could not understand the time '{text}'. "
                             "Use e.g. 'in 10 minutes', 'at 17:30', 'tomorrow 9am' or ISO format.")
    when = dt.datetime.combine(day, dt.time(*hm))
    if when <= now and day == now.date():
        when += dt.timedelta(days=1)
    return when


class Scheduler:
    """Polls the reminders table and fires notifications when they come due."""

    def __init__(self, memory, on_fire: Callable[[str], None] | None = None, interval: float = 2.0):
        self.memory = memory
        self.on_fire: list[Callable[[str], None]] = [on_fire] if on_fire else []
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def add(self, message: str, when: dt.datetime) -> int:
        return self.memory.add_reminder(message, when.timestamp())

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="jarvis-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def check(self) -> list[str]:
        fired = []
        for rem in self.memory.due_reminders():
            self.memory.mark_fired(rem["id"])
            fired.append(rem["message"])
            platform_utils.notify("JARVIS reminder", rem["message"])
            for cb in self.on_fire:
                try:
                    cb(rem["message"])
                except Exception:
                    pass
        return fired

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.check()
            except Exception:
                pass
            self._stop.wait(self.interval)


def describe_due(ts: float) -> str:
    when = dt.datetime.fromtimestamp(ts)
    delta = when - dt.datetime.now()
    mins = int(delta.total_seconds() // 60)
    rel = f"in {mins} min" if 0 <= mins < 120 else ""
    return when.strftime("%a %d %b %H:%M") + (f" ({rel})" if rel else "")

