import { forwardRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { Category, Priority, Reminder, Repeat } from "../types";
import { formatDue, isOverdue, relativeTime } from "../lib/dates";
import {
  AlarmSnoozeIcon,
  CheckIcon,
  ClockIcon,
  EditIcon,
  FlagIcon,
  RepeatIcon,
  TrashIcon,
} from "./Icons";
import { Button, IconButton } from "./ui/Button";

export interface ReminderItemProps {
  reminder: Reminder;
  now: Date;
  onToggle: (id: string) => void;
  onEdit: (r: Reminder) => void;
  onDelete: (id: string) => void;
  onSnooze: (id: string, minutes: number) => void;
}

const SNOOZE_MINUTES = 10;

const PRIORITY_STRIP: Record<Priority, string> = {
  high: "bg-danger",
  medium: "bg-warn",
  low: "bg-muted/40",
};

const PRIORITY_TEXT: Record<Priority, string> = {
  high: "text-danger",
  medium: "text-warn",
  low: "text-muted",
};

const PRIORITY_LABEL: Record<Priority, string> = {
  high: "High priority",
  medium: "Medium priority",
  low: "Low priority",
};

const REPEAT_LABEL: Record<Repeat, string> = {
  none: "",
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
};

const CATEGORY_STYLE: Record<Category, string> = {
  personal: "bg-accent-soft text-accent border-accent/30",
  work: "bg-sky-400/10 text-sky-300 border-sky-400/25",
  health: "bg-ok/10 text-ok border-ok/25",
  shopping: "bg-pink-400/10 text-pink-300 border-pink-400/25",
  other: "bg-surface-2 text-muted border-line",
};

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export const ReminderItem = forwardRef<HTMLLIElement, ReminderItemProps>(
  function ReminderItem({ reminder, now, onToggle, onEdit, onDelete, onSnooze }, ref) {
    const reduceMotion = useReducedMotion();
    const { id, title, notes, dueAt, priority, repeat, category, completed } = reminder;
    const overdue = isOverdue(reminder, now);
    const repeating = repeat !== "none";
    const titleId = `reminder-title-${id}`;

    const toggleLabel = completed
      ? `Mark "${title}" as not done`
      : repeating
        ? `Complete "${title}" and schedule next ${REPEAT_LABEL[repeat].toLowerCase()} occurrence`
        : `Mark "${title}" as done`;

    return (
      <motion.li
        ref={ref}
        layout={reduceMotion ? false : "position"}
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -32, scale: 0.97 }}
        transition={{ type: "spring", stiffness: 420, damping: 34, mass: 0.8 }}
        aria-labelledby={titleId}
        className={[
          "group relative overflow-hidden rounded-2xl border bg-surface",
          "shadow-[0_1px_0_0_rgba(255,255,255,0.03)_inset,0_8px_24px_-12px_rgba(0,0,0,0.6)]",
          "transition-colors duration-200",
          overdue
            ? "border-danger/35 bg-gradient-to-r from-danger/[0.06] to-transparent"
            : "border-line hover:border-line/80 hover:bg-surface-2/60",
          completed ? "opacity-70" : "",
        ].join(" ")}
      >
        {/* Priority accent strip */}
        <span
          aria-hidden="true"
          className={[
            "absolute inset-y-0 left-0 w-1",
            completed ? "bg-line" : PRIORITY_STRIP[priority],
          ].join(" ")}
        />

        <div className="flex items-start gap-2 py-3 pl-3 pr-2 sm:gap-3 sm:py-4 sm:pl-4 sm:pr-3">
          {/* Round checkbox — 40px touch target with a 24px visual circle */}
          <button
            type="button"
            role="checkbox"
            aria-checked={completed}
            aria-label={toggleLabel}
            title={completed ? "Mark as not done" : repeating ? "Done — schedule next" : "Mark as done"}
            onClick={() => onToggle(id)}
            className="-ml-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <motion.span
              aria-hidden="true"
              initial={false}
              animate={completed ? { scale: [0.8, 1.12, 1] } : { scale: 1 }}
              transition={{ duration: 0.28 }}
              className={[
                "flex h-6 w-6 items-center justify-center rounded-full border-2 transition-colors duration-200",
                completed
                  ? "border-ok bg-ok text-app"
                  : overdue
                    ? "border-danger/70 text-transparent hover:border-danger hover:bg-danger/10 hover:text-danger/70"
                    : "border-muted/60 text-transparent hover:border-accent hover:bg-accent-soft hover:text-accent/80",
              ].join(" ")}
            >
              <CheckIcon className="h-3.5 w-3.5" />
            </motion.span>
          </button>

          {/* Main content */}
          <div className="min-w-0 flex-1 pt-2">
            <div className="flex items-start gap-2">
              <h3
                id={titleId}
                className={[
                  "min-w-0 flex-1 break-words text-[15px] font-medium leading-snug",
                  completed ? "text-muted line-through decoration-muted/70" : "text-fg",
                ].join(" ")}
              >
                {title}
              </h3>
              {!completed && priority !== "low" && (
                <span
                  className={`mt-0.5 shrink-0 ${PRIORITY_TEXT[priority]}`}
                  title={PRIORITY_LABEL[priority]}
                >
                  <FlagIcon className="h-4 w-4" />
                  <span className="sr-only">{PRIORITY_LABEL[priority]}</span>
                </span>
              )}
            </div>

            {notes.trim() !== "" && (
              <p
                className={[
                  "mt-1 line-clamp-2 whitespace-pre-line break-words text-sm leading-relaxed",
                  completed ? "text-muted/70" : "text-muted",
                ].join(" ")}
              >
                {notes}
              </p>
            )}

            <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs">
              <span
                className={[
                  "inline-flex items-center gap-1.5 font-medium",
                  overdue ? "text-danger" : "text-muted",
                ].join(" ")}
              >
                <ClockIcon className="h-3.5 w-3.5 shrink-0" />
                <time dateTime={dueAt}>{formatDue(dueAt, now)}</time>
                <span aria-hidden="true" className="opacity-60">
                  ·
                </span>
                <span>
                  {overdue && <span className="sr-only">Overdue, </span>}
                  {relativeTime(dueAt, now)}
                </span>
              </span>

              {repeating && (
                <span className="inline-flex items-center gap-1 rounded-full border border-accent/25 bg-accent-soft px-2 py-0.5 font-medium text-accent">
                  <RepeatIcon className="h-3 w-3" />
                  {REPEAT_LABEL[repeat]}
                </span>
              )}

              <span
                className={`inline-flex items-center rounded-full border px-2 py-0.5 font-medium ${CATEGORY_STYLE[category]}`}
              >
                {capitalize(category)}
              </span>
            </div>

            {overdue && (
              <div className="mt-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onSnooze(id, SNOOZE_MINUTES)}
                  aria-label={`Snooze "${title}" for ${SNOOZE_MINUTES} minutes`}
                  className="min-h-[40px] gap-1.5 border-danger/30 text-danger hover:bg-danger/10"
                >
                  <AlarmSnoozeIcon className="h-4 w-4" />
                  Snooze {SNOOZE_MINUTES} min
                </Button>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex shrink-0 items-center gap-0.5 pt-0 opacity-100 transition-opacity sm:opacity-70 sm:group-focus-within:opacity-100 sm:group-hover:opacity-100">
            {!completed && !overdue && (
              <IconButton
                label={`Snooze ${SNOOZE_MINUTES} minutes`}
                onClick={() => onSnooze(id, SNOOZE_MINUTES)}
                className="h-10 w-10"
              >
                <AlarmSnoozeIcon className="h-[18px] w-[18px]" />
              </IconButton>
            )}
            <IconButton label="Edit reminder" onClick={() => onEdit(reminder)} className="h-10 w-10">
              <EditIcon className="h-[18px] w-[18px]" />
            </IconButton>
            <IconButton
              label="Delete reminder"
              tone="danger"
              onClick={() => onDelete(id)}
              className="h-10 w-10"
            >
              <TrashIcon className="h-[18px] w-[18px]" />
            </IconButton>
          </div>
        </div>
      </motion.li>
    );
  },
);
