"""Agent base class and the shared runtime context."""
from __future__ import annotations

import datetime as dt
import json
import platform
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from .llm import LLMClient, LLMError, StreamFilter
from .tools import Tool, collect_tools

EventSink = Callable[[str, dict[str, Any]], None]
ConfirmFn = Callable[[str], bool]


@dataclass
class Context:
    """Everything an agent needs: config, model, memory, OS helpers, UI hooks."""

    config: Any
    llm: LLMClient
    memory: Any
    scheduler: Any = None
    confirm: ConfirmFn = lambda prompt: False
    events: list[EventSink] = field(default_factory=list)
    speak: Callable[[str], None] | None = None
    # Parallel sub-agents must not prompt the user at the same time.
    confirm_lock: threading.Lock = field(default_factory=threading.Lock)

    def emit(self, kind: str, **data: Any) -> None:
        for sink in list(self.events):
            try:
                sink(kind, data)
            except Exception:
                pass

    def approve(self, prompt: str) -> bool:
        if self.config.get("safety.auto_approve") or not self.config.get("safety.confirm_dangerous", True):
            return True
        with self.confirm_lock:
            return bool(self.confirm(prompt))


def environment_brief() -> str:
    now = dt.datetime.now().astimezone()
    os_name = {"Darwin": "macOS", "Windows": "Windows"}.get(platform.system(), platform.system())
    return (f"Current date/time: {now.strftime('%A %d %B %Y, %H:%M %Z')}. "
            f"Operating system: {os_name} {platform.release()}.")


class Agent:
    """A specialist with its own prompt and tools.

    Subclasses set ``name``, ``description`` (shown to the orchestrator) and
    ``instructions``, and add ``@tool`` methods. An agent with no tools is a
    pure language specialist (writer, translator...).
    """

    name: str = "agent"
    title: str = "Agent"
    description: str = ""
    instructions: str = ""
    temperature: float | None = None
    max_steps: int | None = None
    emit_tool_events: bool = True

    def __init__(self, ctx: Context):
        self.ctx = ctx

    # Subclasses can override to add/borrow tools.
    def get_tools(self) -> list[Tool]:
        return collect_tools(self)

    @property
    def model(self) -> str:
        return self.ctx.config.get("llm.agent_model") or self.ctx.config.get("llm.model")

    def system_prompt(self) -> str:
        cfg = self.ctx.config
        return (
            f"You are the {self.title} sub-agent of {cfg.get('assistant.name')}, a personal AI "
            f"assistant. {self.instructions}\n\n{environment_brief()}\n"
            "Use your tools whenever they help; never invent tool results. When you have "
            "finished, reply with a concise, factual report of what you did and found. "
            "If a tool fails, say so plainly."
        )

    def run(self, task: str, history: list[dict] | None = None,
            on_token: Callable[[str], None] | None = None) -> str:
        tools = self.get_tools()
        by_name = {t.name: t for t in tools}
        schemas = [t.schema() for t in tools] or None
        messages: list[dict] = [{"role": "system", "content": self.system_prompt()}]
        messages += history or []
        messages.append({"role": "user", "content": task})
        max_steps = self.max_steps or int(self.ctx.config.get("agents.max_steps", 8))

        for _ in range(max_steps):
            stream = StreamFilter(on_token) if on_token else None
            resp = self.ctx.llm.chat(messages, tools=schemas, model=self.model,
                                     temperature=self.temperature,
                                     on_token=stream.feed if stream else None)
            if stream:
                stream.flush()
            if not resp.tool_calls:
                return resp.content.strip()
            messages.append({"role": "assistant", "content": resp.content,
                             "tool_calls": resp.tool_calls})
            for call in resp.tool_calls:
                result = self._execute(by_name, call.name, call.arguments)
                messages.append({"role": "tool", "name": call.name,
                                 "tool_call_id": call.id, "content": result})

        # Out of steps: ask for a final answer without tools.
        messages.append({"role": "user", "content":
                         "Stop using tools now and give your best final answer."})
        stream = StreamFilter(on_token) if on_token else None
        resp = self.ctx.llm.chat(messages, model=self.model,
                                 on_token=stream.feed if stream else None)
        if stream:
            stream.flush()
        return resp.content.strip()

    def _execute(self, by_name: dict[str, Tool], name: str, args: dict[str, Any]) -> str:
        tool = by_name.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'. Available: {', '.join(by_name)}"
        if self.emit_tool_events:
            self.ctx.emit("tool", agent=self.name, tool=name, args=args)
        if tool.dangerous:
            pretty = json.dumps(args, ensure_ascii=False)
            if len(pretty) > 400:
                pretty = pretty[:400] + "..."
            if not self.ctx.approve(f"[{self.title}] wants to run {name} {pretty}"):
                self.ctx.emit("tool_result", agent=self.name, tool=name, result="declined")
                return "The user declined this action. Do not retry it; explain what you would have done."
        try:
            result = tool.run(args)
        except LLMError as exc:
            result = f"Error: {exc}"
        if self.emit_tool_events:
            self.ctx.emit("tool_result", agent=self.name, tool=name, result=result[:300])
        return result
