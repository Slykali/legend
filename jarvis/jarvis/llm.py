"""Local LLM client.

Talks to Ollama (``/api/chat``) or any OpenAI-compatible local server
(``/v1/chat/completions``) using only the standard library. Supports native
tool calling and falls back to parsing JSON tool calls out of plain text,
because small local models do not always use the native format.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str = field(default_factory=lambda: "call_" + uuid.uuid4().hex[:12])


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMError(RuntimeError):
    pass


def strip_thinking(text: str) -> str:
    text = THINK_RE.sub("", text)
    # An unterminated <think> block means the model is still "thinking".
    if "<think>" in text:
        text = text.split("<think>", 1)[0]
    return text.strip()


def _parse_args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"input": parsed}
        except json.JSONDecodeError:
            return {"input": raw}
    return {}


def _json_objects(text: str) -> Iterable[dict]:
    """Yield every top-level JSON object embedded in ``text``."""
    decoder = json.JSONDecoder()
    i = 0
    while True:
        start = text.find("{", i)
        if start < 0:
            return
        try:
            obj, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            i = start + 1
            continue
        if isinstance(obj, dict):
            yield obj
        i = end


def extract_text_tool_calls(content: str, known: set[str]) -> list[ToolCall]:
    """Find tool calls a model wrote as text instead of using native tools.

    Accepts shapes like ``{"name": "x", "arguments": {...}}``,
    ``{"tool": "x", "args": {...}}`` and ``{"function": {"name": ..}}``,
    optionally wrapped in code fences or ``<tool_call>`` tags. Only names in
    ``known`` are accepted so ordinary JSON in an answer is left alone.
    """
    calls: list[ToolCall] = []
    for obj in _json_objects(content):
        if isinstance(obj.get("function"), dict):
            obj = obj["function"]
        name = obj.get("name") or obj.get("tool") or obj.get("tool_name")
        if not isinstance(name, str) or name not in known:
            continue
        args = obj.get("arguments", obj.get("args", obj.get("parameters", {})))
        calls.append(ToolCall(name=name, arguments=_parse_args(args)))
    return calls


class StreamFilter:
    """Filters a token stream before it reaches the user.

    Hides ``<think>`` blocks and suppresses output that turns out to be a
    text-format tool call (starts with ``{``, a code fence or ``<tool_call>``).
    """

    PROBE = 12

    def __init__(self, sink: Callable[[str], None]):
        self.sink = sink
        self.buffer = ""
        self.decided = False
        self.suppress = False
        self.in_think = False

    def feed(self, token: str) -> None:
        if self.suppress:
            return
        self.buffer += token
        while True:
            if self.in_think:
                end = self.buffer.find("</think>")
                if end < 0:
                    return
                self.buffer = self.buffer[end + len("</think>"):]
                self.in_think = False
                continue
            start = self.buffer.find("<think>")
            if start >= 0:
                before = self.buffer[:start]
                self.buffer = self.buffer[start + len("<think>"):]
                self.in_think = True
                if before:
                    self._emit(before)
                continue
            break
        if not self.decided:
            probe = self.buffer.lstrip()
            if not probe:
                return
            if probe.startswith(("{", "```json", "<tool_call>", "[{")):
                self.suppress = True
                self.buffer = ""
                return
            if len(probe) < self.PROBE and not probe.endswith((" ", "\n")):
                # Hold back a few characters ("<thi", "``") until we can tell.
                if "<" in probe or "`" in probe:
                    return
            self.decided = True
            self.buffer = probe
        # Keep a possible partial "<think>" tag in the buffer.
        cut = self.buffer.rfind("<")
        if cut >= 0 and "<think>".startswith(self.buffer[cut:]):
            out, self.buffer = self.buffer[:cut], self.buffer[cut:]
        else:
            out, self.buffer = self.buffer, ""
        if out:
            self._emit(out)

    def _emit(self, text: str) -> None:
        self.decided = True
        self.sink(text)

    def flush(self) -> None:
        if not self.suppress and not self.in_think and self.buffer:
            text, self.buffer = self.buffer, ""
            if self.decided or not text.lstrip().startswith("{"):
                self.sink(text)


class LLMClient:
    def __init__(self, config):
        self.config = config
        self.provider = config.get("llm.provider", "ollama").lower()
        self.base_url = config.get("llm.base_url", "http://localhost:11434").rstrip("/")
        self.model = config.get("llm.model")
        self.timeout = float(config.get("llm.timeout", 300))
        self._embed_disabled = False

    # ------------------------------------------------------------------ http
    def _request(self, path: str, payload: dict | None = None, stream: bool = False):
        url = self.base_url + path
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"}
        key = self.config.get("llm.api_key")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:500]
            raise LLMError(f"{exc.code} from {url}: {body}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise LLMError(
                f"Cannot reach the local model server at {self.base_url} ({exc}). "
                "Is Ollama running? Start it with 'ollama serve'."
            ) from exc
        if stream:
            return resp
        with resp:
            return json.loads(resp.read().decode())

    # -------------------------------------------------------------- messages
    def _to_ollama(self, messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            msg: dict[str, Any] = {"role": m["role"], "content": m.get("content") or ""}
            if m.get("tool_calls"):
                msg["tool_calls"] = [
                    {"function": {"name": c.name, "arguments": c.arguments}}
                    for c in m["tool_calls"]
                ]
            if m["role"] == "tool" and m.get("name"):
                msg["tool_name"] = m["name"]
            if m.get("images"):
                msg["images"] = m["images"]
            out.append(msg)
        return out

    def _to_openai(self, messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m.get("images"):
                parts: list[dict] = [{"type": "text", "text": m.get("content") or ""}]
                for img in m["images"]:
                    parts.append({"type": "image_url",
                                  "image_url": {"url": f"data:image/png;base64,{img}"}})
                out.append({"role": m["role"], "content": parts})
                continue
            msg: dict[str, Any] = {"role": m["role"], "content": m.get("content") or ""}
            if m.get("tool_calls"):
                msg["tool_calls"] = [
                    {"id": c.id, "type": "function",
                     "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                    for c in m["tool_calls"]
                ]
            if m["role"] == "tool":
                msg["tool_call_id"] = m.get("tool_call_id", "")
            out.append(msg)
        return out

    # ------------------------------------------------------------------ chat
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> LLMResponse:
        model = model or self.model
        temp = self.config.get("llm.temperature", 0.4) if temperature is None else temperature
        if self.provider == "openai":
            resp = self._chat_openai(messages, tools, model, temp, on_token)
        else:
            resp = self._chat_ollama(messages, tools, model, temp, on_token)
        if not resp.tool_calls and tools:
            known = {t["function"]["name"] for t in tools}
            resp.tool_calls = extract_text_tool_calls(strip_thinking(resp.content), known)
            if resp.tool_calls:
                resp.content = ""
        resp.content = strip_thinking(resp.content)
        return resp

    def _chat_ollama(self, messages, tools, model, temp, on_token) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._to_ollama(messages),
            "stream": on_token is not None,
            "keep_alive": self.config.get("llm.keep_alive", "30m"),
            "options": {"temperature": temp, "num_ctx": int(self.config.get("llm.num_ctx", 8192))},
        }
        if tools:
            payload["tools"] = tools
        if on_token is None:
            data = self._request("/api/chat", payload)
            msg = data.get("message", {})
            calls = [ToolCall(c["function"]["name"], _parse_args(c["function"].get("arguments")))
                     for c in msg.get("tool_calls") or []]
            return LLMResponse(msg.get("content", ""), calls)

        content, calls = [], []
        with self._request("/api/chat", payload, stream=True) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if chunk.get("error"):
                    raise LLMError(chunk["error"])
                msg = chunk.get("message", {})
                for c in msg.get("tool_calls") or []:
                    calls.append(ToolCall(c["function"]["name"],
                                          _parse_args(c["function"].get("arguments"))))
                token = msg.get("content", "")
                if token:
                    content.append(token)
                    on_token(token)
                if chunk.get("done"):
                    break
        return LLMResponse("".join(content), calls)

    def _chat_openai(self, messages, tools, model, temp, on_token) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._to_openai(messages),
            "temperature": temp,
        }
        if tools:
            payload["tools"] = tools
        # Streaming tool-call deltas vary between servers; only stream plain answers.
        if on_token is not None and not tools:
            payload["stream"] = True
            content = []
            with self._request("/v1/chat/completions", payload, stream=True) as resp:
                for raw in resp:
                    line = raw.decode().strip()
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if body == "[DONE]":
                        break
                    delta = json.loads(body)["choices"][0].get("delta", {})
                    token = delta.get("content") or ""
                    if token:
                        content.append(token)
                        on_token(token)
            return LLMResponse("".join(content))

        data = self._request("/v1/chat/completions", payload)
        msg = data["choices"][0]["message"]
        calls = [ToolCall(c["function"]["name"], _parse_args(c["function"].get("arguments")),
                          c.get("id") or "call_" + uuid.uuid4().hex[:12])
                 for c in msg.get("tool_calls") or []]
        content = msg.get("content") or ""
        if on_token and content and not calls:
            on_token(content)
        return LLMResponse(content, calls)

    # ------------------------------------------------------------- utilities
    def complete(self, prompt: str, system: str = "", model: str | None = None,
                 temperature: float | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, model=model, temperature=temperature).content

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        """Return embeddings, or None if no embedding model is available."""
        model = self.config.get("llm.embed_model")
        if self._embed_disabled or not model or not texts:
            return None
        try:
            if self.provider == "openai":
                data = self._request("/v1/embeddings", {"model": model, "input": texts})
                return [d["embedding"] for d in data["data"]]
            data = self._request("/api/embed", {"model": model, "input": texts})
            return data.get("embeddings")
        except (LLMError, KeyError, ValueError):
            # Missing model or unsupported endpoint: fall back to keyword search.
            self._embed_disabled = True
            return None

    def list_models(self) -> list[str]:
        if self.provider == "openai":
            data = self._request("/v1/models")
            return [m["id"] for m in data.get("data", [])]
        data = self._request("/api/tags")
        return [m["name"] for m in data.get("models", [])]

    def health(self) -> tuple[bool, str]:
        try:
            models = self.list_models()
        except LLMError as exc:
            return False, str(exc)
        return True, f"{len(models)} model(s) available"
