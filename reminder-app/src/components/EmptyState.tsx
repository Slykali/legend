import type { FilterView } from "../types";
import { EmptyIllustration } from "./Illustration";
import { Button } from "./ui/Button";
import { PlusIcon } from "./Icons";

const COPY: Record<FilterView, { title: string; body: string }> = {
  all: {
    title: "No reminders yet",
    body: "Add your first reminder and we'll nudge you when it's due.",
  },
  today: {
    title: "Nothing due today",
    body: "Your day is clear. Add something if you'd like a nudge.",
  },
  upcoming: {
    title: "Nothing coming up",
    body: "Plan ahead by adding a reminder for later.",
  },
  overdue: {
    title: "Nothing overdue. Nice work.",
    body: "You're all caught up.",
  },
  completed: {
    title: "No completed reminders",
    body: "Reminders you check off will show up here.",
  },
};

const SHOW_ADD: Record<FilterView, boolean> = {
  all: true,
  today: true,
  upcoming: true,
  overdue: false,
  completed: false,
};

export function EmptyState({
  view,
  hasSearch,
  onAdd,
}: {
  view: FilterView;
  hasSearch: boolean;
  onAdd: () => void;
}) {
  const { title, body } = hasSearch
    ? {
        title: "No reminders match your search",
        body: "Try a different word or clear the search and filters.",
      }
    : COPY[view];

  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-surface/50 px-6 py-10 text-center sm:py-14"
    >
      <EmptyIllustration className="mb-5 h-32 w-32 sm:h-40 sm:w-40" />
      <h2 className="text-base font-semibold text-fg sm:text-lg">{title}</h2>
      <p className="mt-1.5 max-w-xs text-sm text-muted">{body}</p>
      {SHOW_ADD[view] && (
        <Button variant="primary" onClick={onAdd} className="mt-6">
          <PlusIcon className="h-4 w-4" />
          New reminder
        </Button>
      )}
    </div>
  );
}
