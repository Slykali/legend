import type { ReactNode } from "react";
import { AnimatePresence } from "framer-motion";
import type { Reminder } from "../types";
import { ReminderItem } from "./ReminderItem";

export interface ReminderListProps {
  reminders: Reminder[];
  now: Date;
  onToggle: (id: string) => void;
  onEdit: (r: Reminder) => void;
  onDelete: (id: string) => void;
  onSnooze: (id: string, minutes: number) => void;
  empty: ReactNode;
}

export function ReminderList({
  reminders,
  now,
  onToggle,
  onEdit,
  onDelete,
  onSnooze,
  empty,
}: ReminderListProps) {
  if (reminders.length === 0) {
    return <>{empty}</>;
  }

  return (
    <ul className="relative flex flex-col gap-2.5 sm:gap-3" aria-label="Reminders">
      <AnimatePresence initial={false} mode="popLayout">
        {reminders.map((r) => (
          <ReminderItem
            key={r.id}
            reminder={r}
            now={now}
            onToggle={onToggle}
            onEdit={onEdit}
            onDelete={onDelete}
            onSnooze={onSnooze}
          />
        ))}
      </AnimatePresence>
    </ul>
  );
}
