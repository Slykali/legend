"""Long-term memory, conversation log, todos and reminders in one SQLite file.

Memories are searched semantically when an embedding model is available
(``nomic-embed-text`` by default) and by keyword overlap otherwise.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    embedding TEXT,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    due TEXT,
    priority TEXT DEFAULT 'normal',
    done INTEGER DEFAULT 0,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    due REAL NOT NULL,
    fired INTEGER DEFAULT 0,
    created REAL NOT NULL
);
"""

WORD_RE = re.compile(r"[a-z0-9]+")
STOP = set("a an the is are was were be to of and or in on at for with my me i you your it this that "
           "what who when where how do does did".split())


def _words(text: str) -> set[str]:
    return {w for w in WORD_RE.findall(text.lower()) if w not in STOP}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class Memory:
    def __init__(self, path: Path | str, llm=None):
        self.llm = llm
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.executescript(SCHEMA)
            self.db.commit()

    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.lock:
            cur = self.db.execute(sql, params)
            self.db.commit()
            return cur

    def _rows(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, params).fetchall()]

    # -------------------------------------------------------------- memories
    def _embed(self, text: str) -> list[float] | None:
        if not self.llm:
            return None
        vecs = self.llm.embed([text])
        return vecs[0] if vecs else None

    def remember(self, text: str, category: str = "general") -> int:
        text = text.strip()
        for row in self._rows("SELECT id, text FROM memories"):
            if row["text"].lower() == text.lower():
                return row["id"]
        emb = self._embed(text)
        cur = self._exec(
            "INSERT INTO memories (text, category, embedding, created) VALUES (?, ?, ?, ?)",
            (text, category, json.dumps(emb) if emb else None, time.time()))
        return int(cur.lastrowid)

    def search(self, query: str, limit: int = 5, min_score: float = 0.0) -> list[dict[str, Any]]:
        rows = self._rows("SELECT id, text, category, embedding, created FROM memories")
        if not rows:
            return []
        qvec = self._embed(query) if any(r["embedding"] for r in rows) else None
        qwords = _words(query)
        scored = []
        for r in rows:
            score = 0.0
            if qvec and r["embedding"]:
                score = _cosine(qvec, json.loads(r["embedding"]))
            elif qwords:
                rw = _words(r["text"] + " " + (r["category"] or ""))
                score = len(qwords & rw) / math.sqrt(len(qwords) * max(len(rw), 1))
            if score > min_score:
                scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"id": r["id"], "text": r["text"], "category": r["category"],
                 "score": round(s, 3)} for s, r in scored[:limit]]

    def list_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._rows("SELECT id, text, category FROM memories ORDER BY id DESC LIMIT ?", (limit,))

    def forget(self, memory_id: int) -> bool:
        return self._exec("DELETE FROM memories WHERE id = ?", (memory_id,)).rowcount > 0

    # ---------------------------------------------------------- conversation
    def log_message(self, session: str, role: str, content: str) -> None:
        self._exec("INSERT INTO messages (session, role, content, created) VALUES (?, ?, ?, ?)",
                   (session, role, content, time.time()))

    def recent_messages(self, session: str, limit: int = 20) -> list[dict[str, str]]:
        rows = self._rows("SELECT role, content FROM messages WHERE session = ? "
                          "ORDER BY id DESC LIMIT ?", (session, limit))
        return list(reversed(rows))

    # ----------------------------------------------------------------- todos
    def add_todo(self, text: str, due: str = "", priority: str = "normal") -> int:
        cur = self._exec("INSERT INTO todos (text, due, priority, created) VALUES (?, ?, ?, ?)",
                         (text, due or None, priority, time.time()))
        return int(cur.lastrowid)

    def list_todos(self, include_done: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT id, text, due, priority, done FROM todos"
        if not include_done:
            sql += " WHERE done = 0"
        return self._rows(sql + " ORDER BY done, CASE priority WHEN 'high' THEN 0 "
                                "WHEN 'normal' THEN 1 ELSE 2 END, id")

    def complete_todo(self, todo_id: int) -> bool:
        return self._exec("UPDATE todos SET done = 1 WHERE id = ?", (todo_id,)).rowcount > 0

    def delete_todo(self, todo_id: int) -> bool:
        return self._exec("DELETE FROM todos WHERE id = ?", (todo_id,)).rowcount > 0

    # ------------------------------------------------------------- reminders
    def add_reminder(self, message: str, due: float) -> int:
        cur = self._exec("INSERT INTO reminders (message, due, created) VALUES (?, ?, ?)",
                         (message, due, time.time()))
        return int(cur.lastrowid)

    def pending_reminders(self) -> list[dict[str, Any]]:
        return self._rows("SELECT id, message, due FROM reminders WHERE fired = 0 ORDER BY due")

    def due_reminders(self, now: float | None = None) -> list[dict[str, Any]]:
        return self._rows("SELECT id, message, due FROM reminders WHERE fired = 0 AND due <= ?",
                          (now or time.time(),))

    def mark_fired(self, reminder_id: int) -> None:
        self._exec("UPDATE reminders SET fired = 1 WHERE id = ?", (reminder_id,))

    def cancel_reminder(self, reminder_id: int) -> bool:
        return self._exec("DELETE FROM reminders WHERE id = ? AND fired = 0",
                          (reminder_id,)).rowcount > 0
