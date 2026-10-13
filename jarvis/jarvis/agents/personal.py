"""Personal organisation: long-term memory, todos/reminders/timers and notes."""
from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path

from ..agent import Agent
from ..scheduler import describe_due, parse_when
from ..tools import tool


class MemoryAgent(Agent):
    name = "memory"
    title = "Memory"
    description = ("Long-term memory about the user: remember facts and preferences, recall "
                   "them, list or forget them.")
    instructions = ("You manage long-term memory. Store facts as short, self-contained "
                    "statements in third person (e.g. 'The user's sister is called Ana').")

    @tool
    def remember(self, fact: str, category: str = "general") -> str:
        """Store a fact in long-term memory.

        Args:
            fact: Short self-contained statement.
            category: e.g. personal, preference, work, contact, health.
        """
        mid = self.ctx.memory.remember(fact, category)
        return f"Stored as memory #{mid}."

    @tool
    def recall(self, query: str, limit: int = 5) -> list[dict] | str:
        """Search long-term memory.

        Args:
            query: What to look for.
            limit: Maximum results.
        """
        return self.ctx.memory.search(query, int(limit)) or "Nothing relevant in memory."

    @tool
    def list_memories(self, limit: int = 30) -> list[dict] | str:
        """List the most recent memories.

        Args:
            limit: Maximum results.
        """
        return self.ctx.memory.list_memories(int(limit)) or "Memory is empty."

    @tool(dangerous=True)
    def forget(self, memory_id: int) -> str:
        """Delete a memory by its id.

        Args:
            memory_id: Id from recall or list_memories.
        """
        return "Forgotten." if self.ctx.memory.forget(int(memory_id)) else "No such memory."


class TasksAgent(Agent):
    name = "tasks"
    title = "Tasks"
    description = "To-do list, reminders at a given time, and countdown timers."
    instructions = ("You keep the user organised. For reminders pass times like 'in 20 minutes', "
                    "'at 17:30', 'tomorrow 9am' or ISO 'YYYY-MM-DD HH:MM'.")

    @tool
    def add_todo(self, text: str, due: str = "", priority: str = "normal") -> str:
        """Add an item to the to-do list.

        Args:
            text: The task.
            due: Optional due date/description.
            priority: low, normal or high.
        """
        tid = self.ctx.memory.add_todo(text, due, priority if priority in ("low", "normal", "high") else "normal")
        return f"Added to-do #{tid}."

    @tool
    def list_todos(self, include_done: bool = False) -> list[dict] | str:
        """Show the to-do list.

        Args:
            include_done: Also show completed items.
        """
        return self.ctx.memory.list_todos(include_done) or "The to-do list is empty."

    @tool
    def complete_todo(self, todo_id: int) -> str:
        """Mark a to-do as done.

        Args:
            todo_id: The to-do number.
        """
        return "Marked done." if self.ctx.memory.complete_todo(int(todo_id)) else "No such to-do."

    @tool
    def delete_todo(self, todo_id: int) -> str:
        """Remove a to-do.

        Args:
            todo_id: The to-do number.
        """
        return "Deleted." if self.ctx.memory.delete_todo(int(todo_id)) else "No such to-do."

    @tool
    def set_reminder(self, message: str, when: str) -> str:
        """Schedule a reminder notification.

        Args:
            message: What to remind the user about.
            when: e.g. 'in 15 minutes', 'at 18:00', 'tomorrow 9am', '2026-03-01 10:00'.
        """
        due = parse_when(when)
        rid = self.ctx.memory.add_reminder(message, due.timestamp())
        return f"Reminder #{rid} set for {describe_due(due.timestamp())}: {message}"

    @tool
    def start_timer(self, minutes: float, label: str = "Timer") -> str:
        """Start a countdown timer.

        Args:
            minutes: Duration in minutes (decimals allowed).
            label: Name of the timer.
        """
        due = dt.datetime.now() + dt.timedelta(minutes=float(minutes))
        rid = self.ctx.memory.add_reminder(f"{label} finished ({minutes:g} min)", due.timestamp())
        return f"Timer #{rid} running, ends at {due:%H:%M:%S}."

    @tool
    def list_reminders(self) -> list[dict] | str:
        """List upcoming reminders and timers."""
        rows = self.ctx.memory.pending_reminders()
        return [{"id": r["id"], "message": r["message"], "due": describe_due(r["due"])}
                for r in rows] or "No upcoming reminders."

    @tool
    def cancel_reminder(self, reminder_id: int) -> str:
        """Cancel a reminder or timer.

        Args:
            reminder_id: Its number.
        """
        return "Cancelled." if self.ctx.memory.cancel_reminder(int(reminder_id)) else "No such reminder."


def _slug(title: str) -> str:
    slug = re.sub(r"[^\w\- ]+", "", title).strip().replace(" ", "-").lower()
    return slug[:80] or "note"


class NotesAgent(Agent):
    name = "notes"
    title = "Notes"
    description = "Create, read, append to, search and delete the user's markdown notes."
    instructions = "You keep the user's notebook (markdown files)."

    def _path(self, title: str) -> Path:
        return self.ctx.config.notes_dir / f"{_slug(title)}.md"

    def _find(self, title: str) -> Path | None:
        exact = self._path(title)
        if exact.exists():
            return exact
        needle = _slug(title)
        for p in sorted(self.ctx.config.notes_dir.glob("*.md")):
            if needle in p.stem:
                return p
        return None

    @tool
    def create_note(self, title: str, content: str) -> str:
        """Create a new note (overwrites a note with the same title).

        Args:
            title: Note title.
            content: Markdown body.
        """
        p = self._path(title)
        p.write_text(f"# {title}\n\n_{dt.datetime.now():%Y-%m-%d %H:%M}_\n\n{content}\n", encoding="utf-8")
        return f"Saved note '{title}' ({p})."

    @tool
    def append_to_note(self, title: str, content: str) -> str:
        """Add text to the end of a note (creates it if missing).

        Args:
            title: Note title.
            content: Text to add.
        """
        p = self._find(title) or self._path(title)
        if not p.exists():
            return self.create_note(title, content)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(f"\n{content}\n")
        return f"Appended to '{p.stem}'."

    @tool
    def read_note(self, title: str) -> str:
        """Read a note.

        Args:
            title: Note title (partial match allowed).
        """
        p = self._find(title)
        return p.read_text(encoding="utf-8") if p else f"No note called '{title}'."

    @tool
    def list_notes(self) -> list[str] | str:
        """List all notes."""
        notes = sorted(self.ctx.config.notes_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [f"{p.stem} ({dt.datetime.fromtimestamp(p.stat().st_mtime):%Y-%m-%d})" for p in notes] or "No notes yet."

    @tool
    def search_notes(self, query: str) -> list[dict] | str:
        """Search inside all notes.

        Args:
            query: Text to find.
        """
        hits = []
        for p in self.ctx.config.notes_dir.glob("*.md"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if query.lower() in line.lower():
                    hits.append({"note": p.stem, "line": line.strip()[:200]})
        return hits[:30] or f"'{query}' not found in notes."

    @tool(dangerous=True)
    def delete_note(self, title: str) -> str:
        """Delete a note (moved to JARVIS trash).

        Args:
            title: Note title.
        """
        p = self._find(title)
        if not p:
            return f"No note called '{title}'."
        shutil.move(str(p), str(self.ctx.config.trash_dir / p.name))
        return f"Deleted note '{p.stem}'."
