import type { Reminder, Repeat } from "../types";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

const weekdayFmt = new Intl.DateTimeFormat("en-GB", { weekday: "short" });
const monthFmt = new Intl.DateTimeFormat("en-GB", { month: "short" });

/** Parse an ISO string into a Date, or null when invalid/empty. */
function parse(iso: string): Date | null {
  if (typeof iso !== "string" || iso.trim() === "") return null;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : new Date(t);
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function sameLocalDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function addLocalDays(d: Date, days: number): Date {
  const r = new Date(d.getTime());
  r.setDate(r.getDate() + days);
  return r;
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function formatTime(d: Date): string {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/**
 * Human-friendly due label, e.g. "Today, 14:30", "Tomorrow, 09:00",
 * "Mon, 14 Oct, 09:00" (year appended when not the current year).
 */
export function formatDue(iso: string, now: Date = new Date()): string {
  const d = parse(iso);
  if (!d) return "No date";
  const time = formatTime(d);
  if (sameLocalDay(d, now)) return `Today, ${time}`;
  if (sameLocalDay(d, addLocalDays(now, 1))) return `Tomorrow, ${time}`;
  if (sameLocalDay(d, addLocalDays(now, -1))) return `Yesterday, ${time}`;
  const weekday = weekdayFmt.format(d);
  const month = monthFmt.format(d);
  const year = d.getFullYear() !== now.getFullYear() ? ` ${d.getFullYear()}` : "";
  return `${weekday}, ${d.getDate()} ${month}${year}, ${time}`;
}

/** Compact relative time, e.g. "in 5 min", "2 h ago", "just now". */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const d = parse(iso);
  if (!d) return "";
  const diff = d.getTime() - now.getTime();
  const abs = Math.abs(diff);
  if (abs < MINUTE) return "just now";

  let label: string;
  const minutes = Math.round(abs / MINUTE);
  const hours = Math.round(abs / HOUR);
  const days = Math.round(abs / DAY);
  if (minutes < 60) {
    label = `${minutes} min`;
  } else if (hours < 24) {
    label = `${hours} h`;
  } else if (days < 7) {
    label = `${days} ${days === 1 ? "day" : "days"}`;
  } else if (days < 30) {
    const w = Math.round(days / 7);
    label = `${w} ${w === 1 ? "week" : "weeks"}`;
  } else if (days < 365) {
    const m = Math.max(1, Math.round(days / 30));
    label = `${m} ${m === 1 ? "month" : "months"}`;
  } else {
    const y = Math.max(1, Math.round(days / 365));
    label = `${y} ${y === 1 ? "year" : "years"}`;
  }
  return diff > 0 ? `in ${label}` : `${label} ago`;
}

/** True when the ISO timestamp falls on the same local calendar day as `now`. */
export function isToday(iso: string, now: Date = new Date()): boolean {
  const d = parse(iso);
  return d ? sameLocalDay(d, now) : false;
}

/** True when the reminder is incomplete and its due time has passed. */
export function isOverdue(r: Reminder, now: Date = new Date()): boolean {
  if (r.completed) return false;
  const d = parse(r.dueAt);
  return d ? d.getTime() < now.getTime() : false;
}

/**
 * Next occurrence in local time: +1 day, +7 days or +1 calendar month
 * (day clamped to month end). "none" or an invalid ISO returns `iso` unchanged.
 */
export function nextOccurrence(iso: string, repeat: Repeat): string {
  if (repeat === "none") return iso;
  const d = parse(iso);
  if (!d) return iso;
  switch (repeat) {
    case "daily":
      return addLocalDays(d, 1).toISOString();
    case "weekly":
      return addLocalDays(d, 7).toISOString();
    case "monthly": {
      const day = d.getDate();
      const r = new Date(d.getTime());
      r.setDate(1);
      r.setMonth(r.getMonth() + 1);
      r.setDate(Math.min(day, daysInMonth(r.getFullYear(), r.getMonth())));
      return r.toISOString();
    }
    default:
      return iso;
  }
}

/**
 * Applies nextOccurrence at least once, and keeps applying it until the
 * result is strictly after `now`. "none" or an invalid ISO returns `iso`.
 */
export function advancePast(iso: string, repeat: Repeat, now: Date = new Date()): string {
  if (repeat === "none" || !parse(iso)) return iso;
  const target = now.getTime();
  let current = iso;
  // Safety cap: ~270 years of daily steps.
  for (let i = 0; i < 100_000; i++) {
    current = nextOccurrence(current, repeat);
    if (Date.parse(current) > target) return current;
  }
  return current;
}

/** "YYYY-MM-DDTHH:mm" in local time for <input type="datetime-local">; "" if invalid. */
export function toLocalInputValue(iso: string): string {
  const d = parse(iso);
  if (!d) return "";
  return (
    `${String(d.getFullYear()).padStart(4, "0")}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

/** Inverse of toLocalInputValue: local "YYYY-MM-DDTHH:mm[:ss]" -> ISO; "" if invalid/empty. */
export function fromLocalInputValue(value: string): string {
  if (typeof value !== "string") return "";
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?$/.exec(value.trim());
  if (!m) return "";
  const [year, month, day, hour, minute] = [m[1], m[2], m[3], m[4], m[5]].map(Number);
  const second = m[6] ? Number(m[6]) : 0;
  if (month < 1 || month > 12 || day < 1 || hour > 23 || minute > 59 || second > 59) return "";
  if (day > daysInMonth(year, month - 1)) return "";
  const d = new Date(year, month - 1, day, hour, minute, second, 0);
  if (d.getFullYear() !== year) d.setFullYear(year); // guard for years < 100
  return Number.isNaN(d.getTime()) ? "" : d.toISOString();
}

/** ISO of the next full hour strictly after `now`. */
export function defaultDueAt(now: Date = new Date()): string {
  const d = new Date(now.getTime());
  d.setMinutes(0, 0, 0);
  d.setHours(d.getHours() + 1);
  return d.toISOString();
}
