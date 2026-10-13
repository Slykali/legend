import { CATEGORIES, PRIORITIES, REPEATS } from "../types";
import type { Category, Priority, Reminder, Repeat } from "../types";

export const STORAGE_KEY = "remind.reminders.v1";

/** Returns the Storage object if usable, otherwise null. Never throws. */
function getStorage(): Storage | null {
  try {
    const ls = (globalThis as { localStorage?: Storage }).localStorage;
    return ls ?? null;
  } catch {
    return null;
  }
}

export function createId(): string {
  try {
    const c = (globalThis as { crypto?: Crypto }).crypto;
    if (c && typeof c.randomUUID === "function") {
      return c.randomUUID();
    }
  } catch {
    // fall through to fallback
  }
  const rand = () => Math.random().toString(36).slice(2, 10);
  return `${Date.now().toString(36)}-${rand()}-${rand()}`;
}

function isValidIso(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && !Number.isNaN(Date.parse(value));
}

function pick<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : fallback;
}

/** Validate and normalise an unknown value into a Reminder, or null if unusable. */
function sanitizeReminder(raw: unknown): Reminder | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const o = raw as Record<string, unknown>;

  if (typeof o.id !== "string" || o.id.trim() === "") return null;
  if (typeof o.title !== "string" || o.title.trim() === "") return null;
  if (!isValidIso(o.dueAt)) return null;

  const completed = o.completed === true;
  const completedAt = completed && isValidIso(o.completedAt) ? o.completedAt : null;

  return {
    id: o.id,
    title: o.title,
    notes: typeof o.notes === "string" ? o.notes : "",
    dueAt: o.dueAt,
    priority: pick<Priority>(o.priority, PRIORITIES, "medium"),
    repeat: pick<Repeat>(o.repeat, REPEATS, "none"),
    category: pick<Category>(o.category, CATEGORIES, "other"),
    completed,
    completedAt,
    notifiedFor: typeof o.notifiedFor === "string" ? o.notifiedFor : null,
    createdAt: isValidIso(o.createdAt) ? o.createdAt : o.dueAt,
  };
}

export function loadReminders(): Reminder[] {
  try {
    const storage = getStorage();
    if (!storage) return [];
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    const seen = new Set<string>();
    const result: Reminder[] = [];
    for (const item of parsed) {
      const r = sanitizeReminder(item);
      if (r && !seen.has(r.id)) {
        seen.add(r.id);
        result.push(r);
      }
    }
    return result;
  } catch {
    return [];
  }
}

export function saveReminders(list: Reminder[]): void {
  try {
    const storage = getStorage();
    if (!storage) return;
    const serialized = JSON.stringify(list);
    // Skip identical writes so cross-tab `storage` events don't ping-pong.
    if (storage.getItem(STORAGE_KEY) === serialized) return;
    storage.setItem(STORAGE_KEY, serialized);
  } catch {
    // Quota exceeded, private mode, etc. — ignore.
  }
}
