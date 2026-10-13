import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent, ReactNode } from "react";
import type { Category, Priority, Reminder, ReminderInput, Repeat } from "../types";
import { CATEGORIES, PRIORITIES, REPEATS } from "../types";
import { Modal } from "./ui/Modal";
import { Button } from "./ui/Button";
import { CalendarIcon, ClockIcon, FlagIcon, RepeatIcon } from "./Icons";
import {
  defaultDueAt,
  formatDue,
  fromLocalInputValue,
  relativeTime,
  toLocalInputValue,
} from "../lib/dates";

const TITLE_MAX = 120;

type QuickPickId = "15m" | "1h" | "tonight" | "tomorrow";

interface QuickPick {
  id: QuickPickId;
  label: string;
  compute: (now: Date) => Date;
}

const QUICK_PICKS: QuickPick[] = [
  {
    id: "15m",
    label: "In 15 min",
    compute: (now) => withZeroSeconds(new Date(now.getTime() + 15 * 60_000)),
  },
  {
    id: "1h",
    label: "In 1 hour",
    compute: (now) => withZeroSeconds(new Date(now.getTime() + 60 * 60_000)),
  },
  {
    id: "tonight",
    label: "Tonight 20:00",
    compute: (now) => {
      const d = new Date(now);
      d.setHours(20, 0, 0, 0);
      // Already past 20:00? Roll over to tomorrow evening.
      if (d.getTime() <= now.getTime()) d.setDate(d.getDate() + 1);
      return d;
    },
  },
  {
    id: "tomorrow",
    label: "Tomorrow 09:00",
    compute: (now) => {
      const d = new Date(now);
      d.setDate(d.getDate() + 1);
      d.setHours(9, 0, 0, 0);
      return d;
    },
  },
];

const PRIORITY_META: Record<Priority, { label: string; dot: string; active: string }> = {
  low: {
    label: "Low",
    dot: "bg-muted",
    active: "bg-surface text-fg ring-1 ring-muted/40",
  },
  medium: {
    label: "Medium",
    dot: "bg-warn",
    active: "bg-warn/15 text-warn ring-1 ring-warn/40",
  },
  high: {
    label: "High",
    dot: "bg-danger",
    active: "bg-danger/15 text-danger ring-1 ring-danger/40",
  },
};

const REPEAT_LABELS: Record<Repeat, string> = {
  none: "Doesn't repeat",
  daily: "Every day",
  weekly: "Every week",
  monthly: "Every month",
};

function withZeroSeconds(d: Date): Date {
  d.setSeconds(0, 0);
  return d;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent";

const fieldBase =
  "w-full rounded-xl border bg-surface-2 px-3.5 py-2.5 text-base text-fg placeholder:text-muted/70 " +
  "transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent";

function fieldClass(invalid: boolean): string {
  return `${fieldBase} ${invalid ? "border-danger/70" : "border-line hover:border-muted/50"}`;
}

export function ReminderForm({
  open,
  initial,
  onClose,
  onSubmit,
}: {
  open: boolean;
  initial: Reminder | null;
  onClose: () => void;
  onSubmit: (input: ReminderInput) => void;
}) {
  const uid = useId();
  const ids = {
    title: `${uid}-title`,
    titleErr: `${uid}-title-err`,
    titleCount: `${uid}-title-count`,
    notes: `${uid}-notes`,
    due: `${uid}-due`,
    dueHint: `${uid}-due-hint`,
    priority: `${uid}-priority`,
    repeat: `${uid}-repeat`,
    category: `${uid}-category`,
  };

  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [dueLocal, setDueLocal] = useState("");
  const [priority, setPriority] = useState<Priority>("medium");
  const [repeat, setRepeat] = useState<Repeat>("none");
  const [category, setCategory] = useState<Category>("personal");
  const [activeChip, setActiveChip] = useState<QuickPickId | null>(null);
  const [touched, setTouched] = useState({ title: false, due: false });
  const [submitted, setSubmitted] = useState(false);

  const titleRef = useRef<HTMLInputElement>(null);
  const dueRef = useRef<HTMLInputElement>(null);
  const priorityRefs = useRef<Array<HTMLButtonElement | null>>([]);

  // Reset all fields whenever the form is opened (from `initial` or defaults).
  useEffect(() => {
    if (!open) return;
    if (initial) {
      setTitle(initial.title);
      setNotes(initial.notes);
      setDueLocal(toLocalInputValue(initial.dueAt));
      setPriority(initial.priority);
      setRepeat(initial.repeat);
      setCategory(initial.category);
    } else {
      setTitle("");
      setNotes("");
      setDueLocal(toLocalInputValue(defaultDueAt()));
      setPriority("medium");
      setRepeat("none");
      setCategory("personal");
    }
    setActiveChip(null);
    setTouched({ title: false, due: false });
    setSubmitted(false);

    // Modal focuses its first focusable element on open; take focus for the
    // title field right after so the user can start typing immediately.
    const t = window.setTimeout(() => {
      const el = titleRef.current;
      if (el) {
        el.focus();
        const end = el.value.length;
        el.setSelectionRange(end, end);
      }
    }, 60);
    return () => window.clearTimeout(t);
  }, [open, initial]);

  const dueIso = useMemo(() => fromLocalInputValue(dueLocal), [dueLocal]);
  const trimmedTitle = title.trim();

  const titleError = trimmedTitle === "" ? "Give your reminder a title." : null;
  const dueError =
    dueLocal.trim() === ""
      ? "Choose when you want to be reminded."
      : dueIso === ""
        ? "That date and time isn't valid."
        : null;

  const showTitleError = (touched.title || submitted) && titleError !== null;
  const showDueError = (touched.due || submitted) && dueError !== null;

  const now = new Date();
  const isPast = dueIso !== "" && Date.parse(dueIso) < now.getTime();
  const duePreview = dueIso !== "" ? `${formatDue(dueIso, now)} · ${relativeTime(dueIso, now)}` : null;

  function handleSubmit(e?: FormEvent) {
    e?.preventDefault();
    setSubmitted(true);
    if (titleError) {
      titleRef.current?.focus();
      return;
    }
    if (dueError) {
      dueRef.current?.focus();
      return;
    }
    onSubmit({
      title: trimmedTitle.slice(0, TITLE_MAX),
      notes: notes.trim(),
      dueAt: dueIso,
      priority,
      repeat,
      category,
    });
  }

  function applyQuickPick(pick: QuickPick) {
    setDueLocal(toLocalInputValue(pick.compute(new Date()).toISOString()));
    setActiveChip(pick.id);
    setTouched((t) => ({ ...t, due: true }));
  }

  function handlePriorityKey(e: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (index + 1) % PRIORITIES.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp")
      next = (index - 1 + PRIORITIES.length) % PRIORITIES.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = PRIORITIES.length - 1;
    else return;
    e.preventDefault();
    setPriority(PRIORITIES[next]);
    priorityRefs.current[next]?.focus();
  }

  function handleNotesKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  }

  const isEdit = initial !== null;
  const titleCountVisible = title.length >= TITLE_MAX - 20;

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? "Edit reminder" : "New reminder"}>
      <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-5">
        {/* Title */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-2">
            <label htmlFor={ids.title} className="text-sm font-medium text-fg">
              Title <span className="text-danger" aria-hidden="true">*</span>
            </label>
            {titleCountVisible && (
              <span
                id={ids.titleCount}
                className={`text-xs tabular-nums ${title.length >= TITLE_MAX ? "text-warn" : "text-muted"}`}
              >
                {title.length}/{TITLE_MAX}
              </span>
            )}
          </div>
          <input
            ref={titleRef}
            id={ids.title}
            type="text"
            autoFocus
            autoComplete="off"
            enterKeyHint="done"
            maxLength={TITLE_MAX}
            required
            placeholder="e.g. Call the dentist"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={() => setTouched((t) => ({ ...t, title: true }))}
            aria-invalid={showTitleError}
            aria-describedby={
              [showTitleError ? ids.titleErr : "", titleCountVisible ? ids.titleCount : ""]
                .filter(Boolean)
                .join(" ") || undefined
            }
            className={fieldClass(showTitleError)}
          />
          {showTitleError && <FieldError id={ids.titleErr}>{titleError}</FieldError>}
        </div>

        {/* Notes */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.notes} className="text-sm font-medium text-fg">
            Notes <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea
            id={ids.notes}
            rows={3}
            placeholder="Add details, links or a checklist…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onKeyDown={handleNotesKey}
            className={`${fieldClass(false)} min-h-[5.5rem] resize-y leading-relaxed`}
          />
        </div>

        {/* Due date-time */}
        <div className="flex flex-col gap-2">
          <label htmlFor={ids.due} className="flex items-center gap-1.5 text-sm font-medium text-fg">
            <CalendarIcon className="h-4 w-4 text-muted" />
            Due <span className="text-danger" aria-hidden="true">*</span>
          </label>

          <div role="group" aria-label="Quick picks" className="flex flex-wrap gap-2">
            {QUICK_PICKS.map((pick) => {
              const active = activeChip === pick.id;
              return (
                <button
                  key={pick.id}
                  type="button"
                  onClick={() => applyQuickPick(pick)}
                  aria-pressed={active}
                  className={`inline-flex min-h-[36px] items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${focusRing} ${
                    active
                      ? "border-accent/60 bg-accent-soft text-fg"
                      : "border-line bg-surface-2 text-muted hover:border-muted/50 hover:text-fg"
                  }`}
                >
                  <ClockIcon className={`h-3.5 w-3.5 ${active ? "text-accent" : ""}`} />
                  {pick.label}
                </button>
              );
            })}
          </div>

          <input
            ref={dueRef}
            id={ids.due}
            type="datetime-local"
            required
            value={dueLocal}
            onChange={(e) => {
              setDueLocal(e.target.value);
              setActiveChip(null);
            }}
            onBlur={() => setTouched((t) => ({ ...t, due: true }))}
            aria-invalid={showDueError}
            aria-describedby={ids.dueHint}
            className={`${fieldClass(showDueError)} min-h-[46px] [color-scheme:dark]`}
          />
          <div id={ids.dueHint} aria-live="polite">
            {showDueError ? (
              <FieldError>{dueError}</FieldError>
            ) : duePreview ? (
              <p className={`text-sm ${isPast ? "text-warn" : "text-muted"}`}>
                {duePreview}
                {isPast && " — this is in the past, you'll be alerted right away."}
              </p>
            ) : null}
          </div>
        </div>

        {/* Priority */}
        <div className="flex flex-col gap-2">
          <span id={ids.priority} className="flex items-center gap-1.5 text-sm font-medium text-fg">
            <FlagIcon className="h-4 w-4 text-muted" />
            Priority
          </span>
          <div
            role="radiogroup"
            aria-labelledby={ids.priority}
            className="grid grid-cols-3 gap-1 rounded-xl border border-line bg-surface-2 p-1"
          >
            {PRIORITIES.map((p, i) => {
              const meta = PRIORITY_META[p];
              const checked = priority === p;
              return (
                <button
                  key={p}
                  ref={(el) => {
                    priorityRefs.current[i] = el;
                  }}
                  type="button"
                  role="radio"
                  aria-checked={checked}
                  tabIndex={checked ? 0 : -1}
                  onClick={() => setPriority(p)}
                  onKeyDown={(e) => handlePriorityKey(e, i)}
                  className={`flex min-h-[40px] items-center justify-center gap-2 rounded-lg px-2 text-sm font-medium transition-colors ${focusRing} ${
                    checked ? meta.active : "text-muted hover:bg-surface/60 hover:text-fg"
                  }`}
                >
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${meta.dot}`} aria-hidden="true" />
                  {meta.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Repeat + Category */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor={ids.repeat} className="flex items-center gap-1.5 text-sm font-medium text-fg">
              <RepeatIcon className="h-4 w-4 text-muted" />
              Repeat
            </label>
            <SelectShell>
              <select
                id={ids.repeat}
                value={repeat}
                onChange={(e) => setRepeat(e.target.value as Repeat)}
                className={`${fieldClass(false)} appearance-none pr-10`}
              >
                {REPEATS.map((r) => (
                  <option key={r} value={r}>
                    {REPEAT_LABELS[r]}
                  </option>
                ))}
              </select>
            </SelectShell>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor={ids.category} className="text-sm font-medium text-fg">
              Category
            </label>
            <SelectShell>
              <select
                id={ids.category}
                value={category}
                onChange={(e) => setCategory(e.target.value as Category)}
                className={`${fieldClass(false)} appearance-none pr-10`}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {capitalize(c)}
                  </option>
                ))}
              </select>
            </SelectShell>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-1 flex flex-col-reverse gap-2 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-end">
          <Button variant="ghost" onClick={onClose} className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button type="submit" variant="primary" className="w-full sm:w-auto">
            {isEdit ? "Save changes" : "Add reminder"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function FieldError({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} role="alert" className="flex items-center gap-1.5 text-sm text-danger">
      <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7.5v5.5" strokeLinecap="round" />
        <circle cx="12" cy="16.5" r="0.6" fill="currentColor" />
      </svg>
      {children}
    </p>
  );
}

function SelectShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative">
      {children}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
      >
        <path d="m6 9 6 6 6-6" />
      </svg>
    </div>
  );
}
