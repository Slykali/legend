import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import type { Reminder } from "../types";
import { CATEGORIES, PRIORITIES, REPEATS } from "../types";
import { STORAGE_KEY, createId, loadReminders, saveReminders } from "./storage";

class MemoryStorage implements Storage {
  private data = new Map<string, string>();

  get length(): number {
    return this.data.size;
  }

  clear(): void {
    this.data.clear();
  }

  getItem(key: string): string | null {
    return this.data.has(key) ? (this.data.get(key) as string) : null;
  }

  key(index: number): string | null {
    return Array.from(this.data.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.data.delete(key);
  }

  setItem(key: string, value: string): void {
    this.data.set(key, String(value));
  }
}

let store: MemoryStorage;

beforeEach(() => {
  store = new MemoryStorage();
  vi.stubGlobal("localStorage", store);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function makeReminder(overrides: Partial<Reminder> = {}): Reminder {
  return {
    id: "r1",
    title: "Water the plants",
    notes: "Balcony ones too",
    dueAt: new Date(2026, 5, 15, 9, 0).toISOString(),
    priority: "high",
    repeat: "weekly",
    category: "personal",
    completed: false,
    completedAt: null,
    notifiedFor: null,
    createdAt: new Date(2026, 5, 1, 8, 0).toISOString(),
    ...overrides,
  };
}

describe("STORAGE_KEY", () => {
  it("is the versioned key from the contract", () => {
    expect(STORAGE_KEY).toBe("remind.reminders.v1");
  });
});

describe("saveReminders / loadReminders", () => {
  it("returns [] when nothing is stored", () => {
    expect(loadReminders()).toEqual([]);
  });

  it("round-trips a list of reminders", () => {
    const list: Reminder[] = [
      makeReminder(),
      makeReminder({
        id: "r2",
        title: "Dentist",
        notes: "",
        priority: "low",
        repeat: "none",
        category: "health",
        completed: true,
        completedAt: new Date(2026, 5, 2, 10, 0).toISOString(),
        notifiedFor: new Date(2026, 5, 15, 9, 0).toISOString(),
      }),
    ];
    saveReminders(list);
    expect(loadReminders()).toEqual(list);
  });

  it("writes JSON under STORAGE_KEY", () => {
    saveReminders([makeReminder()]);
    const raw = store.getItem(STORAGE_KEY);
    expect(raw).not.toBeNull();
    const parsed: unknown = JSON.parse(raw as string);
    expect(Array.isArray(parsed)).toBe(true);
    expect((parsed as unknown[]).length).toBe(1);
  });

  it("round-trips an empty list", () => {
    saveReminders([makeReminder()]);
    saveReminders([]);
    expect(loadReminders()).toEqual([]);
  });

  it("returns [] for corrupt JSON", () => {
    store.setItem(STORAGE_KEY, "{not valid json");
    expect(() => loadReminders()).not.toThrow();
    expect(loadReminders()).toEqual([]);
  });

  it("returns [] when the stored value is not an array", () => {
    store.setItem(STORAGE_KEY, JSON.stringify({ id: "x" }));
    expect(loadReminders()).toEqual([]);
    store.setItem(STORAGE_KEY, JSON.stringify("hello"));
    expect(loadReminders()).toEqual([]);
    store.setItem(STORAGE_KEY, "null");
    expect(loadReminders()).toEqual([]);
  });

  it("drops invalid items and keeps valid ones", () => {
    const valid = makeReminder({ id: "keep" });
    store.setItem(
      STORAGE_KEY,
      JSON.stringify([null, 42, "nope", [], {}, { notes: "no id or title" }, valid]),
    );
    const loaded = loadReminders();
    expect(loaded).toHaveLength(1);
    expect(loaded[0]).toEqual(valid);
  });

  it("fills defaults for missing optional fields", () => {
    const dueAt = new Date(2026, 5, 15, 9, 0).toISOString();
    store.setItem(STORAGE_KEY, JSON.stringify([{ id: "min", title: "Minimal", dueAt }]));
    const loaded = loadReminders();
    expect(loaded).toHaveLength(1);
    const r = loaded[0];
    expect(r.id).toBe("min");
    expect(r.title).toBe("Minimal");
    expect(Date.parse(r.dueAt)).toBe(Date.parse(dueAt));
    expect(r.notes).toBe("");
    expect(PRIORITIES).toContain(r.priority);
    expect(REPEATS).toContain(r.repeat);
    expect(CATEGORIES).toContain(r.category);
    expect(r.completed).toBe(false);
    expect(r.completedAt).toBeNull();
    expect(r.notifiedFor).toBeNull();
    expect(typeof r.createdAt).toBe("string");
  });

  it("replaces unknown enum values with valid ones", () => {
    const bad = { ...makeReminder({ id: "enum" }), priority: "urgent", repeat: "hourly", category: "misc" };
    store.setItem(STORAGE_KEY, JSON.stringify([bad]));
    const loaded = loadReminders();
    // Either sanitized to valid values, or dropped entirely — never passed through as-is.
    for (const r of loaded) {
      expect(PRIORITIES).toContain(r.priority);
      expect(REPEATS).toContain(r.repeat);
      expect(CATEGORIES).toContain(r.category);
    }
  });

  it("loadReminders never throws when localStorage access fails", () => {
    vi.stubGlobal("localStorage", {
      getItem() {
        throw new Error("denied");
      },
      setItem() {
        throw new Error("denied");
      },
    });
    expect(() => loadReminders()).not.toThrow();
    expect(loadReminders()).toEqual([]);
  });

  it("saveReminders never throws when setItem fails (e.g. quota exceeded)", () => {
    vi.stubGlobal("localStorage", {
      getItem() {
        return null;
      },
      setItem() {
        throw new Error("QuotaExceededError");
      },
    });
    expect(() => saveReminders([makeReminder()])).not.toThrow();
  });
});

describe("createId", () => {
  it("returns non-empty unique strings", () => {
    const ids = new Set<string>();
    for (let i = 0; i < 500; i++) {
      const id = createId();
      expect(typeof id).toBe("string");
      expect(id.length).toBeGreaterThan(0);
      ids.add(id);
    }
    expect(ids.size).toBe(500);
  });

  it("still returns unique ids when crypto.randomUUID is unavailable", () => {
    vi.stubGlobal("crypto", {});
    const ids = new Set<string>();
    for (let i = 0; i < 500; i++) {
      const id = createId();
      expect(typeof id).toBe("string");
      expect(id.length).toBeGreaterThan(0);
      ids.add(id);
    }
    expect(ids.size).toBe(500);
  });
});
