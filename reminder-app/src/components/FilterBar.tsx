import { useEffect, useRef } from "react";
import type { KeyboardEvent } from "react";
import { CATEGORIES, FILTER_VIEWS } from "../types";
import type { Category, FilterView, Filters } from "../types";
import { SearchIcon, XIcon } from "./Icons";

export interface FilterBarProps {
  filters: Filters;
  onChange: (f: Filters) => void;
  counts: Record<FilterView, number>;
}

const VIEW_LABELS: Record<FilterView, string> = {
  all: "All",
  today: "Today",
  upcoming: "Upcoming",
  overdue: "Overdue",
  completed: "Completed",
};

const capitalize = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1);

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent";

export function FilterBar({ filters, onChange, counts }: FilterBarProps) {
  const searchRef = useRef<HTMLInputElement>(null);
  const tabRefs = useRef<Partial<Record<FilterView, HTMLButtonElement | null>>>({});

  // Keep the active tab visible inside the scrollable strip (without scrolling the page).
  useEffect(() => {
    const el = tabRefs.current[filters.view];
    const strip = el?.parentElement;
    if (!el || !strip) return;
    // The strip is `relative`, so offsetLeft is measured from it.
    const left = el.offsetLeft;
    const right = left + el.offsetWidth;
    if (left < strip.scrollLeft) {
      strip.scrollTo({ left: Math.max(0, left - 8), behavior: "smooth" });
    } else if (right > strip.scrollLeft + strip.clientWidth) {
      strip.scrollTo({ left: right - strip.clientWidth + 8, behavior: "smooth" });
    }
  }, [filters.view]);

  const setView = (view: FilterView) => {
    if (view !== filters.view) onChange({ ...filters, view });
  };

  const clearSearch = () => {
    onChange({ ...filters, search: "" });
    searchRef.current?.focus();
  };

  const onTabKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    const idx = FILTER_VIEWS.indexOf(filters.view);
    let next: number | null = null;
    switch (e.key) {
      case "ArrowRight":
        next = (idx + 1) % FILTER_VIEWS.length;
        break;
      case "ArrowLeft":
        next = (idx - 1 + FILTER_VIEWS.length) % FILTER_VIEWS.length;
        break;
      case "Home":
        next = 0;
        break;
      case "End":
        next = FILTER_VIEWS.length - 1;
        break;
      default:
        return;
    }
    e.preventDefault();
    const view = FILTER_VIEWS[next];
    setView(view);
    tabRefs.current[view]?.focus();
  };

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="flex min-w-0 items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <label htmlFor="reminder-search" className="sr-only">
            Search reminders
          </label>
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            ref={searchRef}
            id="reminder-search"
            type="search"
            inputMode="search"
            autoComplete="off"
            spellCheck={false}
            placeholder="Search reminders"
            value={filters.search}
            onChange={(e) => onChange({ ...filters, search: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === "Escape" && filters.search) {
                e.preventDefault();
                clearSearch();
              }
            }}
            className={`h-10 w-full min-w-0 rounded-xl border border-line bg-surface-2 pl-9 pr-9 text-base text-fg placeholder:text-muted transition-colors sm:text-sm [&::-webkit-search-cancel-button]:appearance-none [&::-webkit-search-decoration]:appearance-none focus-visible:border-accent ${focusRing}`}
          />
          {filters.search && (
            <button
              type="button"
              onClick={clearSearch}
              aria-label="Clear search"
              title="Clear search"
              className={`absolute right-1.5 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-lg text-muted transition-colors hover:bg-surface hover:text-fg ${focusRing}`}
            >
              <XIcon className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className="relative shrink-0">
          <label htmlFor="reminder-category" className="sr-only">
            Filter by category
          </label>
          <select
            id="reminder-category"
            value={filters.category}
            onChange={(e) =>
              onChange({ ...filters, category: e.target.value as Category | "all" })
            }
            className={`h-10 max-w-[9.5rem] cursor-pointer appearance-none truncate rounded-xl border border-line bg-surface-2 pl-3 pr-8 text-sm text-fg transition-colors hover:border-muted/50 sm:max-w-none focus-visible:border-accent ${focusRing}`}
          >
            <option value="all">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {capitalize(c)}
              </option>
            ))}
          </select>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>
      </div>

      <div
        role="tablist"
        aria-label="Filter reminders"
        className="relative flex w-full min-w-0 gap-1.5 overflow-x-auto overscroll-x-contain rounded-xl p-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {FILTER_VIEWS.map((view) => {
          const selected = filters.view === view;
          const count = counts[view] ?? 0;
          const alert = view === "overdue" && count > 0;
          return (
            <button
              key={view}
              ref={(el) => {
                tabRefs.current[view] = el;
              }}
              type="button"
              role="tab"
              id={`filter-tab-${view}`}
              aria-selected={selected}
              tabIndex={selected ? 0 : -1}
              onClick={() => setView(view)}
              onKeyDown={onTabKeyDown}
              className={`flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${focusRing} ${
                selected
                  ? "border-accent/60 bg-accent-soft text-fg"
                  : "border-line bg-surface text-muted hover:border-muted/50 hover:text-fg"
              }`}
            >
              <span>{VIEW_LABELS[view]}</span>
              <span className="sr-only">
                {`, ${count} ${count === 1 ? "reminder" : "reminders"}`}
              </span>
              <span
                aria-hidden="true"
                className={`min-w-[1.25rem] rounded-full px-1.5 py-px text-center text-xs font-semibold tabular-nums ${
                  alert
                    ? "bg-danger/15 text-danger"
                    : selected
                      ? "bg-accent/25 text-fg"
                      : "bg-surface-2 text-muted"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
