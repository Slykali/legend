import { useCallback, useMemo, useState } from "react";
import { EmptyState } from "./components/EmptyState";
import { FilterBar } from "./components/FilterBar";
import { Header } from "./components/Header";
import { ReminderForm } from "./components/ReminderForm";
import { ReminderList } from "./components/ReminderList";
import { StatsBar } from "./components/StatsBar";
import { useToast } from "./components/Toast";
import { Button } from "./components/ui/Button";
import { useReminders } from "./hooks/useReminders";
import { useNow, useScheduler } from "./hooks/useScheduler";
import { countByView, filterReminders, getStats, sortReminders } from "./lib/filters";
import {
  getPermission,
  playChime,
  requestPermission,
  showNotification,
} from "./lib/notifications";
import type { Filters, Reminder, ReminderInput } from "./types";

const INITIAL_FILTERS: Filters = { view: "all", search: "", category: "all" };

export default function App() {
  const {
    reminders,
    addReminder,
    updateReminder,
    deleteReminder,
    restoreReminder,
    toggleComplete,
    snooze,
    markNotified,
    clearCompleted,
  } = useReminders();
  const toast = useToast();
  const now = useNow();

  const [filters, setFilters] = useState<Filters>(INITIAL_FILTERS);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Reminder | null>(null);
  const [permission, setPermission] = useState(getPermission);

  const handleDue = useCallback(
    (r: Reminder) => {
      markNotified(r.id, r.dueAt);
      showNotification(r);
      playChime();
      toast.show(`⏰ ${r.title}`, {
        tone: "warning",
        durationMs: 8000,
        action: { label: "Snooze 10 min", onClick: () => snooze(r.id, 10) },
      });
    },
    [markNotified, snooze, toast],
  );
  useScheduler(reminders, handleDue);

  const visible = useMemo(
    () => sortReminders(filterReminders(reminders, filters, now)),
    [reminders, filters, now],
  );
  const stats = useMemo(() => getStats(reminders, now), [reminders, now]);
  const counts = useMemo(() => countByView(reminders, now), [reminders, now]);

  const openNew = useCallback(() => {
    setEditing(null);
    setFormOpen(true);
  }, []);

  const openEdit = useCallback((r: Reminder) => {
    setEditing(r);
    setFormOpen(true);
  }, []);

  const closeForm = useCallback(() => setFormOpen(false), []);

  const handleSubmit = (input: ReminderInput) => {
    if (editing) {
      updateReminder(editing.id, input);
      toast.show("Reminder updated", { tone: "success" });
    } else {
      addReminder(input);
      toast.show("Reminder added", { tone: "success" });
    }
    setFormOpen(false);
  };

  const handleDelete = useCallback(
    (id: string) => {
      const removed = deleteReminder(id);
      if (!removed) return;
      toast.show("Reminder deleted", {
        action: { label: "Undo", onClick: () => restoreReminder(removed) },
      });
    },
    [deleteReminder, restoreReminder, toast],
  );

  const handleSnooze = useCallback(
    (id: string, minutes: number) => {
      snooze(id, minutes);
      toast.show(`Snoozed for ${minutes} min`);
    },
    [snooze, toast],
  );

  const handleRequestPermission = async () => {
    const result = await requestPermission();
    setPermission(result);
    if (result === "granted") toast.show("Alerts enabled", { tone: "success" });
    else if (result === "denied")
      toast.show("Alerts are blocked in your browser settings", { tone: "warning" });
  };

  return (
    <div className="min-h-svh">
      <Header
        permission={permission}
        onRequestPermission={handleRequestPermission}
        onAdd={openNew}
      />

      <main
        className="mx-auto w-full max-w-3xl space-y-5 px-4 pt-5 sm:px-6"
        style={{ paddingBottom: "calc(6rem + env(safe-area-inset-bottom))" }}
      >
        <StatsBar stats={stats} />
        <FilterBar filters={filters} onChange={setFilters} counts={counts} />

        <ReminderList
          reminders={visible}
          now={now}
          onToggle={toggleComplete}
          onEdit={openEdit}
          onDelete={handleDelete}
          onSnooze={handleSnooze}
          empty={
            <EmptyState
              view={filters.view}
              hasSearch={filters.search.trim() !== "" || filters.category !== "all"}
              onAdd={openNew}
            />
          }
        />

        {filters.view === "completed" && counts.completed > 0 && (
          <div className="flex justify-center">
            <Button variant="ghost" size="sm" onClick={clearCompleted}>
              Clear completed
            </Button>
          </div>
        )}
      </main>

      <ReminderForm
        open={formOpen}
        initial={editing}
        onClose={closeForm}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
