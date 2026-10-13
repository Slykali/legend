"""JARVIS itself: the orchestrator that talks to the user and delegates to sub-agents."""
from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .agent import Agent, ConfirmFn, Context, environment_brief
from .agents import ALL_AGENTS
from .config import Config
from .llm import LLMClient, LLMError
from .memory import Memory
from .scheduler import Scheduler
from .tools import Tool


class Orchestrator(Agent):
    name = "jarvis"
    title = "JARVIS"
    max_steps = 8
    emit_tool_events = False  # delegation already emits agent_start/agent_end

    def __init__(self, ctx: Context, agents: dict[str, Agent]):
        super().__init__(ctx)
        self.agents = agents
        self.memory_hint = ""
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="jarvis-agent")

    @property
    def model(self) -> str:
        return self.ctx.config.get("llm.model")

    def system_prompt(self) -> str:
        cfg = self.ctx.config
        roster = "\n".join(f"- {a.name}: {a.description}" for a in self.agents.values())
        prompt = (
            f"You are {cfg.get('assistant.name')}, a personal AI assistant running entirely on the "
            f"user's own computer. Address the user as '{cfg.get('assistant.user_name')}'. "
            f"{cfg.get('assistant.personality')}\n\n{environment_brief()}\n\n"
            "You lead a team of specialist sub-agents. Delegate with the `delegate` tool whenever a "
            "task needs real data or an action (files, apps, web, weather, news, reminders, "
            "calculations, memory...). Use `delegate_parallel` for independent sub-tasks, e.g. "
            "weather AND news. Give each sub-agent a complete, self-contained task including every "
            "detail it needs (it cannot see this conversation). Answer directly, without tools, for "
            "chit-chat and general knowledge. Never claim to have done something unless a "
            "sub-agent confirmed it. When the user shares a lasting personal fact or preference, "
            "delegate to `memory` to remember it.\n\n"
            f"Your sub-agents:\n{roster}"
        )
        if self.memory_hint:
            prompt += f"\n\nThings you remember about the user (use if relevant):\n{self.memory_hint}"
        return prompt

    def get_tools(self) -> list[Tool]:
        names = list(self.agents)
        delegate = Tool(
            name="delegate",
            description="Hand a task to one specialist sub-agent and get its report back.",
            func=self.delegate,
            parameters={"type": "object", "properties": {
                "agent": {"type": "string", "enum": names, "description": "Sub-agent name."},
                "task": {"type": "string", "description": "Complete, self-contained instructions."},
            }, "required": ["agent", "task"]},
        )
        parallel = Tool(
            name="delegate_parallel",
            description="Run several independent sub-agent tasks at the same time.",
            func=self.delegate_parallel,
            parameters={"type": "object", "properties": {
                "tasks": {"type": "array", "description": "List of {agent, task} objects.",
                          "items": {"type": "object", "properties": {
                              "agent": {"type": "string", "enum": names},
                              "task": {"type": "string"}}, "required": ["agent", "task"]}},
            }, "required": ["tasks"]},
        )
        return [delegate, parallel]

    def delegate(self, agent: str, task: str) -> str:
        sub = self.agents.get(agent.strip().lower())
        if sub is None:
            return f"No sub-agent named '{agent}'. Choose from: {', '.join(self.agents)}"
        self.ctx.emit("agent_start", agent=sub.name, title=sub.title, task=task)
        started = time.time()
        try:
            result = sub.run(task)
        except LLMError as exc:
            result = f"Error: {exc}"
        except Exception as exc:
            result = f"Sub-agent {sub.name} failed: {type(exc).__name__}: {exc}"
        self.ctx.emit("agent_end", agent=sub.name, title=sub.title, result=result[:500],
                      seconds=round(time.time() - started, 1))
        return f"[{sub.title} agent report]\n{result or '(no output)'}"

    def delegate_parallel(self, tasks: list) -> str:
        if isinstance(tasks, dict):
            tasks = [tasks]
        jobs = [t for t in tasks if isinstance(t, dict) and t.get("agent") and t.get("task")]
        if not jobs:
            return "Error: tasks must be a list of {agent, task} objects."
        futures = [self.pool.submit(self.delegate, j["agent"], j["task"]) for j in jobs[:6]]
        return "\n\n".join(f.result() for f in futures)


class Jarvis:
    """High-level facade used by every interface (CLI, voice, web)."""

    def __init__(self, config: Config | None = None, confirm: ConfirmFn | None = None,
                 speak: Callable[[str], None] | None = None, start_scheduler: bool = True):
        self.config = config or Config.load()
        self.llm = LLMClient(self.config)
        self.memory = Memory(self.config.db_path, self.llm)
        self.ctx = Context(config=self.config, llm=self.llm, memory=self.memory,
                           confirm=confirm or (lambda prompt: False), speak=speak)
        self.scheduler = Scheduler(self.memory, on_fire=self._on_reminder)
        self.ctx.scheduler = self.scheduler
        disabled = {d.lower() for d in self.config.get("agents.disabled", [])}
        self.agents: dict[str, Agent] = {cls.name: cls(self.ctx) for cls in ALL_AGENTS
                                         if cls.name not in disabled}
        self.core = Orchestrator(self.ctx, self.agents)
        self.session = uuid.uuid4().hex[:12]
        self.history: list[dict] = []
        self.lock = threading.Lock()
        self._background: list[threading.Thread] = []
        if start_scheduler:
            self.scheduler.start()

    def _on_reminder(self, message: str) -> None:
        name = self.config.get("assistant.user_name")
        self.ctx.emit("reminder", message=message)
        if self.ctx.speak:
            self.ctx.speak(f"Pardon the interruption, {name}. Reminder: {message}")

    def on_event(self, sink) -> None:
        self.ctx.events.append(sink)

    def ask(self, text: str, on_token: Callable[[str], None] | None = None) -> str:
        """Process one user message and return JARVIS's reply."""
        with self.lock:
            hits = self.memory.search(text, limit=5, min_score=0.15)
            self.core.memory_hint = "\n".join(f"- {h['text']}" for h in hits)
            try:
                reply = self.core.run(text, history=self.history, on_token=on_token)
            except LLMError as exc:
                reply = f"I'm afraid my local model is unavailable: {exc}"
                if on_token:
                    on_token(reply)
            reply = reply or "Done."
            self.history += [{"role": "user", "content": text},
                             {"role": "assistant", "content": reply}]
            keep = int(self.config.get("assistant.history_turns", 12)) * 2
            self.history = self.history[-keep:]
            self.memory.log_message(self.session, "user", text)
            self.memory.log_message(self.session, "assistant", reply)
        if self.config.get("assistant.auto_memory", True):
            worker = threading.Thread(target=self._auto_memory, args=(text,), daemon=True)
            worker.start()
            self._background = [t for t in self._background if t.is_alive()] + [worker]
        return reply

    def _auto_memory(self, text: str) -> None:
        """Quietly extract durable personal facts from what the user said."""
        if len(text.split()) < 4:
            return
        try:
            out = self.llm.complete(
                "Extract durable facts about the user (name, family, preferences, job, location, "
                "habits, important dates) from their message. Ignore requests, questions and "
                "temporary details. Reply ONLY with a JSON list of short third-person statements, "
                f"or [] if none.\n\nMessage: {text}",
                model=self.config.get("llm.agent_model") or self.config.get("llm.model"),
                temperature=0.0)
            start, end = out.find("["), out.rfind("]")
            facts = json.loads(out[start:end + 1]) if 0 <= start < end else []
            for fact in facts[:5]:
                if isinstance(fact, str) and 5 < len(fact) < 300:
                    self.memory.remember(fact, "auto")
        except Exception:
            pass

    def reset(self) -> None:
        with self.lock:
            self.history.clear()
            self.session = uuid.uuid4().hex[:12]

    def shutdown(self) -> None:
        for worker in self._background:
            worker.join(timeout=20)  # let memory extraction finish saving
        self.scheduler.stop()
        self.core.pool.shutdown(wait=False)
