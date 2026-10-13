# Remind

A small reminder app: create reminders with a due time, priority, category and optional repeat
(daily / weekly / monthly), and get a browser notification plus an in-app chime when they come due.

Everything is stored in your browser's `localStorage` — no account or server needed. Changes sync
between open tabs.

## Run it

```bash
cd reminder-app
npm install
npm run dev      # http://localhost:5173
npm test         # unit tests (vitest)
npm run build    # production build in dist/
```

Click **Enable alerts** in the header to allow system notifications. Alerts fire while the app is open
in a tab (the browser has to be running; there is no background push).

## Features

- Quick-pick due times (in 15 min, in 1 hour, tonight, tomorrow morning)
- Today / Upcoming / Overdue / Completed views, search and category filter
- Snooze 10 min, undo delete, clear completed
- Completing a repeating reminder moves it to its next occurrence
- Works from phone width up, keyboard accessible, installable (web manifest)

## Layout

```
src/
  types.ts                 shared types
  App.tsx                  wires everything together
  lib/                     dates, filters, storage, notifications (+ tests)
  hooks/                   useReminders (state + persistence), useScheduler (due checks), useNow
  components/              Header, FilterBar, StatsBar, ReminderForm, ReminderList/Item, EmptyState,
                           Toast, Icons, Illustration, ui/Button, ui/Modal
```
