"""Tool definitions.

Decorate an agent method with ``@tool`` and its signature, type hints and
docstring become a JSON schema the model can call.
"""
from __future__ import annotations

import inspect
import json
import re
import types
import typing
from dataclasses import dataclass
from typing import Any, Callable

MAX_RESULT_CHARS = 6000

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean",
               list: "array", dict: "object"}


def _json_type(annotation: Any) -> dict[str, Any]:
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        return _json_type(args[0]) if args else {"type": "string"}
    if origin is list:
        (item,) = typing.get_args(annotation) or (str,)
        return {"type": "array", "items": _json_type(item)}
    if origin is dict:
        return {"type": "object"}
    return {"type": _JSON_TYPES.get(annotation, "string")}


def _parse_docstring(doc: str) -> tuple[str, dict[str, str]]:
    """Split a docstring into a summary and ``Args:`` descriptions."""
    doc = inspect.cleandoc(doc or "")
    summary, _, rest = doc.partition("Args:")
    params: dict[str, str] = {}
    current = None
    for line in rest.splitlines():
        m = re.match(r"\s*(\w+)\s*(?:\(.*?\))?:\s*(.*)", line)
        if m:
            current = m.group(1)
            params[current] = m.group(2).strip()
        elif current and line.strip():
            params[current] += " " + line.strip()
    return " ".join(summary.split()), params


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict[str, Any]
    dangerous: bool = False

    def schema(self) -> dict[str, Any]:
        return {"type": "function",
                "function": {"name": self.name, "description": self.description,
                             "parameters": self.parameters}}

    def _coerce(self, args: dict[str, Any]) -> dict[str, Any]:
        props = self.parameters.get("properties", {})
        out = {}
        for key, value in args.items():
            if key not in props:
                continue  # models sometimes invent arguments; ignore them
            kind = props[key].get("type")
            try:
                if kind == "integer" and not isinstance(value, int):
                    value = int(float(value))
                elif kind == "number" and not isinstance(value, (int, float)):
                    value = float(value)
                elif kind == "boolean" and isinstance(value, str):
                    value = value.strip().lower() in ("true", "yes", "1", "y")
                elif kind == "array" and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        value = [v.strip() for v in value.split(",") if v.strip()]
                elif kind == "string" and not isinstance(value, str):
                    value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            except (TypeError, ValueError):
                pass
            out[key] = value
        return out

    def run(self, args: dict[str, Any]) -> str:
        args = self._coerce(args or {})
        missing = [p for p in self.parameters.get("required", []) if p not in args]
        if missing:
            return f"Error: missing required argument(s): {', '.join(missing)}"
        try:
            result = self.func(**args)
        except Exception as exc:  # tools must never crash the agent loop
            return f"Error running {self.name}: {type(exc).__name__}: {exc}"
        if result is None:
            text = "Done."
        elif isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, ensure_ascii=False, indent=1, default=str)
        if len(text) > MAX_RESULT_CHARS:
            text = text[:MAX_RESULT_CHARS] + f"\n...[truncated {len(text) - MAX_RESULT_CHARS} chars]"
        return text


def tool(_func=None, *, name: str | None = None, dangerous: bool = False,
         parameters: dict[str, Any] | None = None):
    """Mark a function or method as a tool.

    ``dangerous=True`` makes JARVIS ask for confirmation before running it.
    ``parameters`` overrides the generated JSON schema.
    """
    def wrap(func):
        func._tool_meta = {"name": name or func.__name__, "dangerous": dangerous,
                           "parameters": parameters}
        return func
    return wrap(_func) if _func is not None else wrap


def build_tool(func: Callable[..., Any]) -> Tool:
    meta = getattr(func, "_tool_meta", {}) or {}
    summary, param_docs = _parse_docstring(func.__doc__ or "")
    schema = meta.get("parameters")
    if schema is None:
        hints = typing.get_type_hints(func)
        props: dict[str, Any] = {}
        required: list[str] = []
        for pname, param in inspect.signature(func).parameters.items():
            if pname == "self" or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            prop = _json_type(hints.get(pname, str))
            if pname in param_docs:
                prop["description"] = param_docs[pname]
            if param.default is inspect.Parameter.empty:
                required.append(pname)
            elif param.default is not None:
                prop["default"] = param.default
            props[pname] = prop
        schema = {"type": "object", "properties": props, "required": required}
    return Tool(name=meta.get("name") or func.__name__, description=summary,
                func=func, parameters=schema, dangerous=meta.get("dangerous", False))


def collect_tools(obj: Any) -> list[Tool]:
    """Build Tool objects for every ``@tool``-decorated method on ``obj``."""
    found = []
    for attr in dir(type(obj)):
        member = getattr(type(obj), attr, None)
        if callable(member) and hasattr(member, "_tool_meta"):
            found.append(build_tool(getattr(obj, attr)))
    return found
