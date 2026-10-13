import { useCallback, useEffect, useRef, useState } from "react";
import type { Reminder } from "../types";

export function useScheduler(
  reminders: Reminder[],
  onDue: (r: Reminder) => void,
  intervalMs = 15000,
): void {
  const onDueRef = useRef(onDue);
  const remindersRef = useRef(reminders);
  const firedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    onDueRef.current = onDue;
  }, [onDue]);

  const check = useCallback(() => {
    const now = Date.now();
    const list = remindersRef.current;
    const fired = firedRef.current;
    for (const r of list) {
      if (r.completed) continue;
      const due = Date.parse(r.dueAt);
      if (Number.isNaN(due) || due > now) continue;
      if (r.notifiedFor === r.dueAt) continue;
      const key = `${r.id}:${r.dueAt}`;
      if (fired.has(key)) continue;
      fired.add(key);
      onDueRef.current(r);
    }
  }, []);

  // Check immediately whenever the reminders change (and on mount).
  useEffect(() => {
    remindersRef.current = reminders;
    check();
  }, [reminders, check]);

  // Periodic check plus when the tab becomes visible again.
  useEffect(() => {
    const id = window.setInterval(check, intervalMs);
    const onVisibility = () => {
      if (document.visibilityState === "visible") check();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [intervalMs, check]);
}

export function useNow(intervalMs = 30000): Date {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), intervalMs);
    const onVisibility = () => {
      if (document.visibilityState === "visible") setNow(new Date());
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [intervalMs]);

  return now;
}
