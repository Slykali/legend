"""Registry of all JARVIS sub-agents.

To add your own: subclass ``jarvis.agent.Agent``, give it a unique ``name``,
a ``description`` and some ``@tool`` methods, then append it to ``ALL_AGENTS``.
"""
from __future__ import annotations

from .advisors import FinanceAgent, FitnessAgent, PlannerAgent, TutorAgent
from .desktop import DesktopAgent, MediaAgent, VisionAgent
from .documents import DocumentsAgent
from .files import FilesAgent
from .info import BriefingAgent, NewsAgent, WeatherAgent
from .language import CommsAgent, TranslatorAgent, WriterAgent
from .math import MathAgent
from .personal import MemoryAgent, NotesAgent, TasksAgent
from .system import CodeAgent, ShellAgent, SystemAgent
from .web import ResearchAgent, WebAgent

ALL_AGENTS = [
    SystemAgent, FilesAgent, ShellAgent, CodeAgent,
    WebAgent, ResearchAgent, NewsAgent, WeatherAgent, BriefingAgent,
    MemoryAgent, TasksAgent, NotesAgent, PlannerAgent,
    DesktopAgent, VisionAgent, MediaAgent, DocumentsAgent,
    MathAgent, FinanceAgent, FitnessAgent,
    WriterAgent, TranslatorAgent, CommsAgent, TutorAgent,
]

__all__ = ["ALL_AGENTS"] + [cls.__name__ for cls in ALL_AGENTS]
