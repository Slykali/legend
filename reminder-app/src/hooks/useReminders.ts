import { useCallback, useEffect, useRef, useState } from "react";
import type { Reminder, ReminderInput } from "../types";
import { advancePast } from "../lib/dates";
import { STORAGE_KEY, createId, loadReminders, saveReminders } from "../lib/storage";

export function useReminders() {
  const [reminders, setReminders] = useState<Reminder[]>(() => loadReminders());

  // Mirror of the latest state so handlers can return values synchronously
  // (e.g. deleteReminder) while remaining stable.
  const remindersRef = useRef(reminders);
  remindersRef.current = reminders;

  // Persist on every change. saveReminders skips identical writes, so state
  // received from another tab is not echoed back.
  useEffect(() => {
    saveReminders(reminders);
  }, [reminders]);

  // Cross-tab sync.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== null && e.key !== STORAGE_KEY) return;
      setReminders(loadReminders());
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const addReminder = useCallback((input: ReminderInput): Reminder => {
    const reminder: Reminder = {
      id: createId(),
      title: input.title,
      notes: input.notes,
      dueAt: input.dueAt,
      priority: input.priority,
      repeat: input.repeat,
      category: input.category,
      completed: false,
      completedAt: null,
      notifiedFor: null,
      createdAt: new Date().toISOString(),
    };
    setReminders((prev) => [...prev, reminder]);
    return reminder;
  }, []);

  const updateReminder = useCallback((id: string, patch: Partial<ReminderInput>): void => {
    setReminders((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        const next: Reminder = { ...r };
        if (patch.title !== undefined) next.title = patch.title;
        if (patch.notes !== undefined) next.notes = patch.notes;
        if (patch.priority !== undefined) next.priority = patch.priority;
        if (patch.repeat !== undefined) next.repeat = patch.repeat;
        if (patch.category !== undefined) next.category = patch.category;
        if (patch.dueAt !== undefined && patch.dueAt !== r.dueAt) {
          next.dueAt = patch.dueAt;
          next.notifiedFor = null;
        }
        return next;
      }),
    );
  }, []);

  const deleteReminder = useCallback((id: string): Reminder | undefined => {
    const removed = remindersRef.current.find((r) => r.id === id);
    setReminders((prev) => prev.filter((r) => r.id !== id));
    return removed;
  }, []);

  const restoreReminder = useCallback((reminder: Reminder): void => {
    setReminders((prev) => [...prev.filter((r) => r.id !== reminder.id), reminder]);
  }, []);

  const toggleComplete = useCallback((id: string): void => {
    setReminders((prev) => {
      const now = new Date();
      return prev.map((r) => {
        if (r.id !== id) return r;
        if (!r.completed && r.repeat !== "none") {
          return { ...r, dueAt: advancePast(r.dueAt, r.repeat, now), notifiedFor: null };
        }
        return r.completed
          ? { ...r, completed: false, completedAt: null }
          : { ...r, completed: true, completedAt: now.toISOString() };
      });
    });
  }, []);

  const snooze = useCallback((id: string, minutes: number): void => {
    setReminders((prev) => {
      const dueAt = new Date(Date.now() + minutes * 60_000).toISOString();
      return prev.map((r) =>
        r.id === id
          ? { ...r, dueAt, notifiedFor: null, completed: false, completedAt: null }
          : r,
      );
    });
  }, []);

  const markNotified = useCallback((id: string, dueAt: string): void => {
    setReminders((prev) =>
      prev.map((r) => (r.id === id && r.notifiedFor !== dueAt ? { ...r, notifiedFor: dueAt } : r)),
    );
  }, []);

  const clearCompleted = useCallback((): void => {
    setReminders((prev) => (prev.some((r) => r.completed) ? prev.filter((r) => !r.completed) : prev));
  }, []);

  return {
    reminders,
    addReminder,
    updateReminder,
    deleteReminder,
    restoreReminder,
    toggleComplete,
    snooze,
    markNotified,
    clearCompleted,
  };
}
