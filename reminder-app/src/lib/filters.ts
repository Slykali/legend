import type { FilterView, Filters, Priority, Reminder, Stats } from "../types";
import { FILTER_VIEWS } from "../types";
import { isOverdue, isToday } from "./dates";

const PRIORITY_RANK: Record<Priority, number> = { high: 0, medium: 1, low: 2 };

function time(iso: string | null | undefined): number {
  if (!iso) return NaN;
  return Date.parse(iso);
}

function matchesView(r: Reminder, view: FilterView, now: Date): boolean {
  switch (view) {
    case "all":
      return !r.completed;
    case "today":
      return !r.completed && isToday(r.dueAt, now);
    case "upcoming": {
      const t = time(r.dueAt);
      return !r.completed && !Number.isNaN(t) && t > now.getTime();
    }
    case "overdue":
      return isOverdue(r, now);
    case "completed":
      return r.completed;
    default:
      return true;
  }
}

/** Applies view, search (title + notes, case-insensitive) and category filters. */
export function filterReminders(
  list: Reminder[],
  filters: Filters,
  now: Date = new Date(),
): Reminder[] {
  const query = (filters.search ?? "").trim().toLowerCase();
  const category = filters.category ?? "all";
  return list.filter((r) => {
    if (!matchesView(r, filters.view, now)) return false;
    if (category !== "all" && r.category !== category) return false;
    if (query) {
      const haystack = `${r.title ?? ""}\n${r.notes ?? ""}`.toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    return true;
  });
}

/**
 * Returns a new array: incomplete first (dueAt asc, then high > medium > low),
 * then completed (completedAt desc).
 */
export function sortReminders(list: Reminder[]): Reminder[] {
  return [...list].sort((a, b) => {
    if (a.completed !== b.completed) return a.completed ? 1 : -1;
    if (!a.completed) {
      const ta = time(a.dueAt);
      const tb = time(b.dueAt);
      const da = Number.isNaN(ta) ? Infinity : ta;
      const db = Number.isNaN(tb) ? Infinity : tb;
      if (da !== db) return da < db ? -1 : 1;
      return (PRIORITY_RANK[a.priority] ?? 3) - (PRIORITY_RANK[b.priority] ?? 3);
    }
    const ca = time(a.completedAt);
    const cb = time(b.completedAt);
    const xa = Number.isNaN(ca) ? -Infinity : ca;
    const xb = Number.isNaN(cb) ? -Infinity : cb;
    if (xa === xb) return 0;
    return xa > xb ? -1 : 1;
  });
}

/** total = incomplete, today = incomplete due today, overdue, completed. */
export function getStats(list: Reminder[], now: Date = new Date()): Stats {
  const stats: Stats = { total: 0, today: 0, overdue: 0, completed: 0 };
  for (const r of list) {
    if (r.completed) {
      stats.completed++;
      continue;
    }
    stats.total++;
    if (isToday(r.dueAt, now)) stats.today++;
    if (isOverdue(r, now)) stats.overdue++;
  }
  return stats;
}

/** Count per view, ignoring search and category. */
export function countByView(list: Reminder[], now: Date = new Date()): Record<FilterView, number> {
  const counts = { all: 0, today: 0, upcoming: 0, overdue: 0, completed: 0 } as Record<
    FilterView,
    number
  >;
  for (const r of list) {
    for (const view of FILTER_VIEWS) {
      if (matchesView(r, view, now)) counts[view]++;
    }
  }
  return counts;
}
