import { describe, it, expect } from "vitest";
import type { Filters, Reminder } from "../types";
import { filterReminders, sortReminders, getStats, countByView } from "./filters";

function local(year: number, month: number, day: number, hours = 0, minutes = 0): string {
  return new Date(year, month, day, hours, minutes, 0, 0).toISOString();
}

let seq = 0;
function makeReminder(overrides: Partial<Reminder> = {}): Reminder {
  seq += 1;
  return {
    id: `r${seq}`,
    title: `Reminder ${seq}`,
    notes: "",
    dueAt: local(2026, 5, 15, 18, 0),
    priority: "medium",
    repeat: "none",
    category: "personal",
    completed: false,
    completedAt: null,
    notifiedFor: null,
    createdAt: local(2026, 0, 1, 8, 0),
    ...overrides,
  };
}

function filters(overrides: Partial<Filters> = {}): Filters {
  return { view: "all", search: "", category: "all", ...overrides };
}

function ids(list: Reminder[]): string[] {
  return list.map((r) => r.id);
}

function sortedIds(list: Reminder[]): string[] {
  return ids(list).sort();
}

const now = new Date(2026, 5, 15, 12, 0);

// Fixture set relative to `now` (June 15 2026, 12:00 local).
const todayLater = makeReminder({
  id: "todayLater",
  title: "Buy Milk",
  dueAt: local(2026, 5, 15, 18, 0),
  category: "shopping",
});
const todayEarlier = makeReminder({
  id: "todayEarlier",
  title: "Morning run",
  notes: "Around the PARK",
  dueAt: local(2026, 5, 15, 8, 0),
  category: "health",
});
const tomorrow = makeReminder({
  id: "tomorrow",
  title: "Standup",
  notes: "call the dentist after",
  dueAt: local(2026, 5, 16, 9, 0),
  category: "work",
});
const yesterday = makeReminder({
  id: "yesterday",
  title: "Pay rent",
  dueAt: local(2026, 5, 14, 9, 0),
  category: "personal",
});
const done = makeReminder({
  id: "done",
  title: "Old milk task",
  dueAt: local(2026, 5, 14, 10, 0),
  category: "shopping",
  completed: true,
  completedAt: local(2026, 5, 14, 10, 5),
});

const all: Reminder[] = [todayLater, todayEarlier, tomorrow, yesterday, done];

describe("filterReminders — views", () => {
  it("all = not completed", () => {
    expect(sortedIds(filterReminders(all, filters({ view: "all" }), now))).toEqual(
      ["todayEarlier", "todayLater", "tomorrow", "yesterday"].sort(),
    );
  });

  it("today = not completed and due today", () => {
    expect(sortedIds(filterReminders(all, filters({ view: "today" }), now))).toEqual(
      ["todayEarlier", "todayLater"].sort(),
    );
  });

  it("upcoming = not completed and due after now", () => {
    expect(sortedIds(filterReminders(all, filters({ view: "upcoming" }), now))).toEqual(
      ["todayLater", "tomorrow"].sort(),
    );
  });

  it("overdue = incomplete and due before now", () => {
    expect(sortedIds(filterReminders(all, filters({ view: "overdue" }), now))).toEqual(
      ["todayEarlier", "yesterday"].sort(),
    );
  });

  it("completed = completed only", () => {
    expect(ids(filterReminders(all, filters({ view: "completed" }), now))).toEqual(["done"]);
  });

  it("returns an empty array for an empty list", () => {
    expect(filterReminders([], filters(), now)).toEqual([]);
  });

  it("does not mutate the input", () => {
    const copy = [...all];
    filterReminders(all, filters({ view: "today", search: "milk" }), now);
    expect(all).toEqual(copy);
  });
});

describe("filterReminders — search", () => {
  it("matches title case-insensitively", () => {
    expect(ids(filterReminders(all, filters({ search: "MILK" }), now))).toEqual(["todayLater"]);
  });

  it("matches notes case-insensitively", () => {
    expect(ids(filterReminders(all, filters({ search: "park" }), now))).toEqual([
      "todayEarlier",
    ]);
    expect(ids(filterReminders(all, filters({ search: "Dentist" }), now))).toEqual(["tomorrow"]);
  });

  it("trims the search query", () => {
    expect(ids(filterReminders(all, filters({ search: "  milk  " }), now))).toEqual([
      "todayLater",
    ]);
  });

  it("treats empty / whitespace search as no filter", () => {
    expect(filterReminders(all, filters({ search: "   " }), now)).toHaveLength(4);
    expect(filterReminders(all, filters({ search: "" }), now)).toHaveLength(4);
  });

  it("combines with the view", () => {
    expect(ids(filterReminders(all, filters({ view: "completed", search: "milk" }), now))).toEqual(
      ["done"],
    );
  });

  it("returns nothing when nothing matches", () => {
    expect(filterReminders(all, filters({ search: "zzz-no-match" }), now)).toEqual([]);
  });
});

describe("filterReminders — category", () => {
  it('"all" applies no category filter', () => {
    expect(filterReminders(all, filters({ category: "all" }), now)).toHaveLength(4);
  });

  it("filters by category", () => {
    expect(ids(filterReminders(all, filters({ category: "work" }), now))).toEqual(["tomorrow"]);
    expect(ids(filterReminders(all, filters({ category: "shopping" }), now))).toEqual([
      "todayLater",
    ]);
    expect(
      ids(filterReminders(all, filters({ view: "completed", category: "shopping" }), now)),
    ).toEqual(["done"]);
    expect(filterReminders(all, filters({ category: "other" }), now)).toEqual([]);
  });

  it("combines category and search", () => {
    expect(
      filterReminders(all, filters({ category: "work", search: "milk" }), now),
    ).toEqual([]);
    expect(
      ids(filterReminders(all, filters({ category: "shopping", search: "milk" }), now)),
    ).toEqual(["todayLater"]);
  });
});

describe("sortReminders", () => {
  it("sorts incomplete reminders by dueAt ascending", () => {
    const a = makeReminder({ id: "a", dueAt: local(2026, 5, 17, 9, 0) });
    const b = makeReminder({ id: "b", dueAt: local(2026, 5, 15, 9, 0) });
    const c = makeReminder({ id: "c", dueAt: local(2026, 5, 16, 9, 0) });
    expect(ids(sortReminders([a, b, c]))).toEqual(["b", "c", "a"]);
  });

  it("breaks dueAt ties by priority high > medium > low", () => {
    const due = local(2026, 5, 15, 9, 0);
    const low = makeReminder({ id: "low", dueAt: due, priority: "low" });
    const high = makeReminder({ id: "high", dueAt: due, priority: "high" });
    const medium = makeReminder({ id: "medium", dueAt: due, priority: "medium" });
    expect(ids(sortReminders([low, medium, high]))).toEqual(["high", "medium", "low"]);
  });

  it("dueAt takes precedence over priority", () => {
    const earlyLow = makeReminder({ id: "earlyLow", dueAt: local(2026, 5, 15, 8, 0), priority: "low" });
    const lateHigh = makeReminder({
      id: "lateHigh",
      dueAt: local(2026, 5, 15, 9, 0),
      priority: "high",
    });
    expect(ids(sortReminders([lateHigh, earlyLow]))).toEqual(["earlyLow", "lateHigh"]);
  });

  it("puts completed reminders last, sorted by completedAt descending", () => {
    const c1 = makeReminder({
      id: "c1",
      dueAt: local(2026, 5, 1, 9, 0),
      completed: true,
      completedAt: local(2026, 5, 10, 9, 0),
    });
    const c2 = makeReminder({
      id: "c2",
      dueAt: local(2026, 5, 2, 9, 0),
      completed: true,
      completedAt: local(2026, 5, 12, 9, 0),
    });
    const open1 = makeReminder({ id: "open1", dueAt: local(2026, 7, 1, 9, 0) });
    const open2 = makeReminder({ id: "open2", dueAt: local(2026, 6, 1, 9, 0) });
    expect(ids(sortReminders([c1, open1, c2, open2]))).toEqual(["open2", "open1", "c2", "c1"]);
  });

  it("returns a new array and does not mutate the input", () => {
    const a = makeReminder({ id: "a", dueAt: local(2026, 5, 17, 9, 0) });
    const b = makeReminder({ id: "b", dueAt: local(2026, 5, 15, 9, 0) });
    const input = [a, b];
    const result = sortReminders(input);
    expect(result).not.toBe(input);
    expect(ids(input)).toEqual(["a", "b"]);
    expect(ids(result)).toEqual(["b", "a"]);
  });

  it("handles an empty list", () => {
    expect(sortReminders([])).toEqual([]);
  });
});

describe("getStats", () => {
  it("counts incomplete, today, overdue and completed", () => {
    expect(getStats(all, now)).toEqual({ total: 4, today: 2, overdue: 2, completed: 1 });
  });

  it("returns zeros for an empty list", () => {
    expect(getStats([], now)).toEqual({ total: 0, today: 0, overdue: 0, completed: 0 });
  });

  it("does not count a completed reminder due today in today", () => {
    const doneToday = makeReminder({
      dueAt: local(2026, 5, 15, 10, 0),
      completed: true,
      completedAt: local(2026, 5, 15, 10, 1),
    });
    expect(getStats([doneToday], now)).toEqual({ total: 0, today: 0, overdue: 0, completed: 1 });
  });
});

describe("countByView", () => {
  it("counts each view", () => {
    expect(countByView(all, now)).toEqual({
      all: 4,
      today: 2,
      upcoming: 2,
      overdue: 2,
      completed: 1,
    });
  });

  it("matches filterReminders for each view with no search/category", () => {
    const counts = countByView(all, now);
    for (const view of ["all", "today", "upcoming", "overdue", "completed"] as const) {
      expect(counts[view]).toBe(filterReminders(all, filters({ view }), now).length);
    }
  });

  it("returns zeros for an empty list", () => {
    expect(countByView([], now)).toEqual({
      all: 0,
      today: 0,
      upcoming: 0,
      overdue: 0,
      completed: 0,
    });
  });
});
