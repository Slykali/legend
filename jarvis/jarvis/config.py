"""Configuration loading.

Settings live in ``~/.jarvis/config.toml`` (override the folder with the
``JARVIS_HOME`` environment variable). Anything missing falls back to
``DEFAULTS`` below, so an empty or absent file is perfectly valid.
"""
from __future__ import annotations

import copy
import os
import tomllib
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "assistant": {
        "name": "JARVIS",
        "user_name": "Sir",
        "personality": (
            "You are calm, witty, loyal and extremely competent, in the style of "
            "Tony Stark's AI butler. Be concise: answer in one to four sentences "
            "unless the user asks for detail. A touch of dry British humour is welcome."
        ),
        "history_turns": 12,
    },
    "llm": {
        # "ollama" or "openai" (any OpenAI-compatible local server: LM Studio,
        # llama.cpp server, vLLM, LocalAI, Jan ...)
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "api_key": "",
        "model": "qwen2.5:7b",
        # Model used by sub-agents. Empty = same as "model". A smaller model
        # (e.g. "qwen2.5:3b") makes sub-agents faster on modest hardware.
        "agent_model": "",
        "embed_model": "nomic-embed-text",
        "vision_model": "llava:7b",
        "temperature": 0.4,
        "num_ctx": 8192,
        "timeout": 300,
        "keep_alive": "30m",
    },
    "voice": {
        "wake_word": "jarvis",
        "stt_model": "base.en",
        "stt_device": "auto",
        "tts_rate": 185,
        "tts_voice": "",
        "follow_up_seconds": 8,
    },
    "safety": {
        # Ask before running shell commands, executing code, deleting/moving
        # files, closing apps and the like.
        "confirm_dangerous": True,
        # Set true to skip confirmations entirely (not recommended).
        "auto_approve": False,
    },
    "server": {"host": "127.0.0.1", "port": 8765},
    "agents": {"disabled": [], "max_steps": 8},
    "weather": {"default_location": "", "units": "metric"},
    "news": {
        "feeds": {
            "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
            "tech": "https://www.theverge.com/rss/index.xml",
            "science": "https://www.sciencedaily.com/rss/all.xml",
            "hackernews": "https://hnrss.org/frontpage",
        }
    },
}


def jarvis_home() -> Path:
    home = os.environ.get("JARVIS_HOME")
    path = Path(home).expanduser() if home else Path.home() / ".jarvis"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class Config:
    def __init__(self, data: dict[str, Any], path: Path | None = None):
        self.data = data
        self.path = path
        self.home = jarvis_home()

    @classmethod
    def load(cls, path: str | os.PathLike | None = None) -> "Config":
        cfg_path = Path(path).expanduser() if path else jarvis_home() / "config.toml"
        user: dict[str, Any] = {}
        if cfg_path.exists():
            with open(cfg_path, "rb") as fh:
                user = tomllib.load(fh)
        return cls(_deep_merge(DEFAULTS, user), cfg_path)

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        node = self.data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    @property
    def db_path(self) -> Path:
        return self.home / "jarvis.db"

    @property
    def notes_dir(self) -> Path:
        path = self.home / "notes"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def trash_dir(self) -> Path:
        path = self.home / "trash"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def workspace_dir(self) -> Path:
        path = self.home / "workspace"
        path.mkdir(parents=True, exist_ok=True)
        return path
