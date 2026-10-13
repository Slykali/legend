import type { ComponentType } from "react";
import type { Stats } from "../types";
import { BellIcon, CalendarIcon, CheckIcon, ClockIcon } from "./Icons";

type Tone = "accent" | "danger" | "ok" | "muted";

interface StatCardProps {
  label: string;
  value: number;
  tone: Tone;
  icon: ComponentType<{ className?: string }>;
}

const TONE_CLASSES: Record<Tone, { card: string; icon: string; value: string }> = {
  accent: {
    card: "border-line bg-surface",
    icon: "bg-accent-soft text-accent",
    value: "text-fg",
  },
  danger: {
    card: "border-danger/40 bg-danger/10",
    icon: "bg-danger/15 text-danger",
    value: "text-danger",
  },
  ok: {
    card: "border-line bg-surface",
    icon: "bg-ok/15 text-ok",
    value: "text-fg",
  },
  muted: {
    card: "border-line bg-surface",
    icon: "bg-surface-2 text-muted",
    value: "text-fg",
  },
};

function StatCard({ label, value, tone, icon: Icon }: StatCardProps) {
  const t = TONE_CLASSES[tone];
  return (
    <li
      className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors ${t.card}`}
    >
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${t.icon}`}
      >
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className={`text-lg font-semibold leading-tight tabular-nums ${t.value}`}>
          {value}
        </p>
        <p className="truncate text-xs text-muted">{label}</p>
      </div>
    </li>
  );
}

export function StatsBar({ stats }: { stats: Stats }) {
  const hasOverdue = stats.overdue > 0;
  return (
    <section aria-label="Reminder summary">
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
        <StatCard label="Active" value={stats.total} tone="accent" icon={BellIcon} />
        <StatCard label="Today" value={stats.today} tone="accent" icon={CalendarIcon} />
        <StatCard
          label="Overdue"
          value={stats.overdue}
          tone={hasOverdue ? "danger" : "muted"}
          icon={ClockIcon}
        />
        <StatCard label="Done" value={stats.completed} tone="ok" icon={CheckIcon} />
      </ul>
    </section>
  );
}
