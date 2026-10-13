export type Priority = "low" | "medium" | "high";
export type Repeat = "none" | "daily" | "weekly" | "monthly";
export type Category = "personal" | "work" | "health" | "shopping" | "other";
export type FilterView = "all" | "today" | "upcoming" | "overdue" | "completed";

export interface Reminder {
  id: string;
  title: string;
  notes: string;
  /** ISO 8601 timestamp of when the reminder is due. */
  dueAt: string;
  priority: Priority;
  repeat: Repeat;
  category: Category;
  completed: boolean;
  completedAt: string | null;
  /** The `dueAt` value a notification has already fired for, or null. */
  notifiedFor: string | null;
  createdAt: string;
}

export type ReminderInput = Pick<
  Reminder,
  "title" | "notes" | "dueAt" | "priority" | "repeat" | "category"
>;

export interface Filters {
  view: FilterView;
  search: string;
  category: Category | "all";
}

export interface Stats {
  total: number;
  today: number;
  overdue: number;
  completed: number;
}

export const PRIORITIES: Priority[] = ["low", "medium", "high"];
export const REPEATS: Repeat[] = ["none", "daily", "weekly", "monthly"];
export const CATEGORIES: Category[] = ["personal", "work", "health", "shopping", "other"];
export const FILTER_VIEWS: FilterView[] = ["all", "today", "upcoming", "overdue", "completed"];
