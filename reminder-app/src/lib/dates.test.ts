import { describe, it, expect } from "vitest";
import type { Reminder } from "../types";
import {
  formatDue,
  relativeTime,
  isToday,
  isOverdue,
  nextOccurrence,
  advancePast,
  toLocalInputValue,
  fromLocalInputValue,
  defaultDueAt,
} from "./dates";

/** ISO string for a local-time calendar date. */
function local(
  year: number,
  month: number,
  day: number,
  hours = 0,
  minutes = 0,
  seconds = 0,
): string {
  return new Date(year, month, day, hours, minutes, seconds, 0).toISOString();
}

function makeReminder(overrides: Partial<Reminder> = {}): Reminder {
  return {
    id: "r1",
    title: "Test reminder",
    notes: "",
    dueAt: local(2026, 0, 1, 9, 0),
    priority: "medium",
    repeat: "none",
    category: "personal",
    completed: false,
    completedAt: null,
    notifiedFor: null,
    createdAt: local(2025, 11, 1, 8, 0),
    ...overrides,
  };
}

function parts(iso: string) {
  const d = new Date(iso);
  return {
    y: d.getFullYear(),
    m: d.getMonth(),
    d: d.getDate(),
    h: d.getHours(),
    min: d.getMinutes(),
  };
}

describe("nextOccurrence", () => {
  it('returns the same value for "none"', () => {
    const iso = local(2026, 0, 31, 9, 0);
    expect(nextOccurrence(iso, "none")).toBe(iso);
  });

  it("adds one day for daily", () => {
    const next = nextOccurrence(local(2026, 0, 31, 9, 0), "daily");
    expect(parts(next)).toEqual({ y: 2026, m: 1, d: 1, h: 9, min: 0 });
  });

  it("adds seven days for weekly", () => {
    const next = nextOccurrence(local(2026, 0, 28, 14, 30), "weekly");
    expect(parts(next)).toEqual({ y: 2026, m: 1, d: 4, h: 14, min: 30 });
  });

  it("keeps the local wall-clock time across a possible DST change", () => {
    // Spans the second Sunday of March (US) / last Sunday of March (EU).
    const weekly = nextOccurrence(local(2026, 2, 5, 9, 0), "weekly");
    expect(parts(weekly)).toEqual({ y: 2026, m: 2, d: 12, h: 9, min: 0 });
    const daily = nextOccurrence(local(2026, 2, 28, 9, 0), "daily");
    expect(parts(daily)).toEqual({ y: 2026, m: 2, d: 29, h: 9, min: 0 });
  });

  it("adds one calendar month for monthly", () => {
    const next = nextOccurrence(local(2026, 0, 15, 9, 0), "monthly");
    expect(parts(next)).toEqual({ y: 2026, m: 1, d: 15, h: 9, min: 0 });
  });

  it("clamps Jan 31 to the end of February (non-leap year)", () => {
    const next = nextOccurrence(local(2026, 0, 31, 9, 0), "monthly");
    expect(parts(next)).toEqual({ y: 2026, m: 1, d: 28, h: 9, min: 0 });
  });

  it("clamps Jan 31 to Feb 29 in a leap year", () => {
    const next = nextOccurrence(local(2028, 0, 31, 9, 0), "monthly");
    expect(parts(next)).toEqual({ y: 2028, m: 1, d: 29, h: 9, min: 0 });
  });

  it("clamps Mar 31 to Apr 30", () => {
    const next = nextOccurrence(local(2026, 2, 31, 18, 45), "monthly");
    expect(parts(next)).toEqual({ y: 2026, m: 3, d: 30, h: 18, min: 45 });
  });

  it("rolls December over into January of the next year", () => {
    const next = nextOccurrence(local(2026, 11, 15, 9, 0), "monthly");
    expect(parts(next)).toEqual({ y: 2027, m: 0, d: 15, h: 9, min: 0 });
  });

  it("returns a parseable ISO string", () => {
    const next = nextOccurrence(local(2026, 0, 1, 9, 0), "daily");
    expect(Number.isNaN(Date.parse(next))).toBe(false);
  });
});

describe("advancePast", () => {
  it('returns the value unchanged for "none"', () => {
    const iso = local(2026, 0, 1, 9, 0);
    const now = new Date(2026, 0, 10, 12, 0);
    expect(advancePast(iso, "none", now)).toBe(iso);
  });

  it("advances a daily reminder to the first occurrence after now", () => {
    const now = new Date(2026, 0, 10, 12, 0);
    const result = advancePast(local(2026, 0, 1, 9, 0), "daily", now);
    expect(Date.parse(result)).toBeGreaterThan(now.getTime());
    expect(parts(result)).toEqual({ y: 2026, m: 0, d: 11, h: 9, min: 0 });
  });

  it("lands on the same day when the time of day is still ahead", () => {
    const now = new Date(2026, 0, 10, 8, 0);
    const result = advancePast(local(2026, 0, 1, 9, 0), "daily", now);
    expect(parts(result)).toEqual({ y: 2026, m: 0, d: 10, h: 9, min: 0 });
  });

  it("advances weekly reminders in whole weeks", () => {
    const now = new Date(2026, 0, 20, 12, 0);
    const result = advancePast(local(2026, 0, 1, 9, 0), "weekly", now);
    expect(Date.parse(result)).toBeGreaterThan(now.getTime());
    expect(parts(result)).toEqual({ y: 2026, m: 0, d: 22, h: 9, min: 0 });
  });

  it("advances monthly reminders past now", () => {
    const now = new Date(2026, 4, 2, 12, 0);
    const result = advancePast(local(2026, 0, 15, 9, 0), "monthly", now);
    expect(Date.parse(result)).toBeGreaterThan(now.getTime());
    expect(parts(result)).toEqual({ y: 2026, m: 4, d: 15, h: 9, min: 0 });
  });

  it("result is strictly after now when due exactly equals now", () => {
    const now = new Date(2026, 0, 10, 9, 0);
    const result = advancePast(now.toISOString(), "daily", now);
    expect(Date.parse(result)).toBeGreaterThan(now.getTime());
    expect(parts(result)).toEqual({ y: 2026, m: 0, d: 11, h: 9, min: 0 });
  });
});

describe("toLocalInputValue / fromLocalInputValue", () => {
  it("formats as YYYY-MM-DDTHH:mm in local time", () => {
    expect(toLocalInputValue(local(2026, 0, 5, 7, 3))).toBe("2026-01-05T07:03");
    expect(toLocalInputValue(local(2026, 10, 25, 23, 59))).toBe("2026-11-25T23:59");
  });

  it("parses a local input value back to the same instant", () => {
    const result = fromLocalInputValue("2026-01-05T07:03");
    expect(Date.parse(result)).toBe(new Date(2026, 0, 5, 7, 3).getTime());
  });

  it("round-trips", () => {
    const iso = local(2026, 6, 4, 16, 20);
    expect(Date.parse(fromLocalInputValue(toLocalInputValue(iso)))).toBe(Date.parse(iso));
    expect(toLocalInputValue(fromLocalInputValue("2026-12-31T00:00"))).toBe("2026-12-31T00:00");
  });

  it('returns "" for empty or invalid input', () => {
    expect(fromLocalInputValue("")).toBe("");
    expect(fromLocalInputValue("not a date")).toBe("");
    expect(fromLocalInputValue("2026-13-45T99:99")).toBe("");
  });
});

describe("defaultDueAt", () => {
  it("returns the next full hour", () => {
    const now = new Date(2026, 0, 5, 9, 15, 30);
    expect(Date.parse(defaultDueAt(now))).toBe(new Date(2026, 0, 5, 10, 0, 0, 0).getTime());
  });

  it("is strictly after now when now is exactly on the hour", () => {
    const now = new Date(2026, 0, 5, 9, 0, 0, 0);
    expect(Date.parse(defaultDueAt(now))).toBe(new Date(2026, 0, 5, 10, 0, 0, 0).getTime());
  });

  it("rolls over to the next day", () => {
    const now = new Date(2026, 0, 5, 23, 30);
    expect(Date.parse(defaultDueAt(now))).toBe(new Date(2026, 0, 6, 0, 0, 0, 0).getTime());
  });
});

describe("isToday", () => {
  const now = new Date(2026, 5, 15, 12, 0);

  it("is true for the same local calendar day", () => {
    expect(isToday(local(2026, 5, 15, 0, 0), now)).toBe(true);
    expect(isToday(local(2026, 5, 15, 23, 59), now)).toBe(true);
  });

  it("is false for other days", () => {
    expect(isToday(local(2026, 5, 14, 23, 59), now)).toBe(false);
    expect(isToday(local(2026, 5, 16, 0, 1), now)).toBe(false);
    expect(isToday(local(2025, 5, 15, 12, 0), now)).toBe(false);
  });
});

describe("isOverdue", () => {
  const now = new Date(2026, 5, 15, 12, 0);

  it("is true for incomplete reminders due in the past", () => {
    expect(isOverdue(makeReminder({ dueAt: local(2026, 5, 15, 11, 59) }), now)).toBe(true);
  });

  it("is false for future reminders", () => {
    expect(isOverdue(makeReminder({ dueAt: local(2026, 5, 15, 12, 1) }), now)).toBe(false);
  });

  it("ignores completed reminders", () => {
    const r = makeReminder({
      dueAt: local(2026, 5, 10, 9, 0),
      completed: true,
      completedAt: local(2026, 5, 10, 9, 5),
    });
    expect(isOverdue(r, now)).toBe(false);
  });
});

describe("formatDue", () => {
  const now = new Date(2026, 5, 15, 12, 0);

  it('contains "Today" for today', () => {
    expect(formatDue(local(2026, 5, 15, 14, 30), now)).toContain("Today");
  });

  it('contains "Tomorrow" for tomorrow', () => {
    expect(formatDue(local(2026, 5, 16, 9, 0), now)).toContain("Tomorrow");
  });

  it("does not say Today/Tomorrow for other days", () => {
    const s = formatDue(local(2026, 5, 20, 9, 0), now);
    expect(s).not.toContain("Today");
    expect(s).not.toContain("Tomorrow");
  });

  it("includes the year when not the current year", () => {
    expect(formatDue(local(2027, 2, 3, 9, 0), now)).toContain("2027");
  });

  it("omits the year for dates in the current year", () => {
    expect(formatDue(local(2026, 8, 3, 9, 0), now)).not.toContain("2026");
  });
});

describe("relativeTime", () => {
  const now = new Date(2026, 5, 15, 12, 0);

  it("describes future times with 'in'", () => {
    expect(relativeTime(new Date(now.getTime() + 5 * 60_000).toISOString(), now)).toMatch(/^in /);
    expect(relativeTime(new Date(now.getTime() + 3 * 86_400_000).toISOString(), now)).toMatch(
      /^in /,
    );
  });

  it("describes past times with 'ago'", () => {
    expect(relativeTime(new Date(now.getTime() - 5 * 60_000).toISOString(), now)).toMatch(/ago$/);
    expect(relativeTime(new Date(now.getTime() - 2 * 3_600_000).toISOString(), now)).toMatch(
      /ago$/,
    );
  });

  it('says "just now" for the current instant', () => {
    expect(relativeTime(now.toISOString(), now)).toBe("just now");
  });
});
