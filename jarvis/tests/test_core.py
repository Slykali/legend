"""Unit and integration tests. Run with:  python -m unittest discover -s tests"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TMP = tempfile.mkdtemp(prefix="jarvis-test-")
os.environ["JARVIS_HOME"] = TMP

from jarvis.agent import Context  # noqa: E402
from jarvis.agents.math import convert, safe_eval  # noqa: E402
from jarvis.agents.system import is_blocked  # noqa: E402
from jarvis.agents.web import _ddg_results, html_to_text  # noqa: E402
from jarvis.agents.info import parse_feed  # noqa: E402
from jarvis.config import Config  # noqa: E402
from jarvis.llm import LLMClient, LLMResponse, StreamFilter, ToolCall, extract_text_tool_calls  # noqa: E402
from jarvis.memory import Memory  # noqa: E402
from jarvis.orchestrator import Jarvis  # noqa: E402
from jarvis.scheduler import Scheduler, parse_when  # noqa: E402
from jarvis.tools import build_tool, tool  # noqa: E402
from jarvis.voice import clean_for_speech, match_wake_word  # noqa: E402


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


class ScriptedLLM(LLMClient):
    """LLM double: pops a scripted response per chat() call and records requests."""

    def __init__(self, config, script):
        super().__init__(config)
        self.script = list(script)
        self.calls = []

    def chat(self, messages, tools=None, model=None, temperature=None, on_token=None):
        self.calls.append({"messages": messages, "tools": tools})
        resp = self.script.pop(0) if self.script else LLMResponse("(script exhausted)")
        if on_token and resp.content:
            on_token(resp.content)
        return resp

    def embed(self, texts):
        return None


# --------------------------------------------------------------------- tools
class ToolSchemaTests(unittest.TestCase):
    def test_schema_from_signature(self):
        @tool(dangerous=True)
        def sample(name: str, count: int = 3, ratio: float | None = None, tags: list[str] | None = None):
            """Do a thing.

            Args:
                name: The name.
                count: How many
                    (continued line).
            """
            return {"name": name, "count": count}

        t = build_tool(sample)
        params = t.parameters
        self.assertTrue(t.dangerous)
        self.assertEqual(t.description, "Do a thing.")
        self.assertEqual(params["required"], ["name"])
        self.assertEqual(params["properties"]["count"]["type"], "integer")
        self.assertEqual(params["properties"]["ratio"]["type"], "number")
        self.assertEqual(params["properties"]["tags"], {"type": "array", "items": {"type": "string"}})
        self.assertIn("continued line", params["properties"]["count"]["description"])

    def test_run_coerces_and_reports_errors(self):
        @tool
        def add(a: int, b: int = 1):
            """Add."""
            return a + b

        t = build_tool(add)
        self.assertEqual(t.run({"a": "4", "b": 2.0, "bogus": 1}), "6")
        self.assertIn("missing required", t.run({}))

        @tool
        def boom():
            """Fail."""
            raise ValueError("nope")
        self.assertIn("ValueError: nope", build_tool(boom).run({}))


class TextToolCallTests(unittest.TestCase):
    known = {"delegate", "calculate"}

    def test_shapes(self):
        cases = [
            '{"name": "calculate", "arguments": {"expression": "2+2"}}',
            '```json\n{"tool": "calculate", "args": {"expression": "2+2"}}\n```',
            '<tool_call>{"function": {"name": "calculate", "arguments": "{\\"expression\\": \\"2+2\\"}"}}</tool_call>',
        ]
        for text in cases:
            calls = extract_text_tool_calls(text, self.known)
            self.assertEqual(len(calls), 1, text)
            self.assertEqual(calls[0].arguments, {"expression": "2+2"})

    def test_ignores_unknown_and_plain_json(self):
        self.assertEqual(extract_text_tool_calls('{"name": "rm_rf", "arguments": {}}', self.known), [])
        self.assertEqual(extract_text_tool_calls('Here is data: {"a": 1}', self.known), [])


class StreamFilterTests(unittest.TestCase):
    def run_filter(self, tokens):
        out = []
        f = StreamFilter(out.append)
        for t in tokens:
            f.feed(t)
        f.flush()
        return "".join(out)

    def test_plain_text_passes(self):
        self.assertEqual(self.run_filter(["Hello", " there", ", Sir."]), "Hello there, Sir.")

    def test_hides_thinking(self):
        self.assertEqual(self.run_filter(["<thi", "nk>secret plan</th", "ink>Answer", " here"]), "Answer here")

    def test_suppresses_text_tool_call(self):
        self.assertEqual(self.run_filter(['{"name"', ': "delegate"}']), "")
        self.assertEqual(self.run_filter(["```js", "on\n{}```"]), "")


# -------------------------------------------------------------------- memory
class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.mem = Memory(":memory:")

    def test_remember_and_search_keywords(self):
        self.mem.remember("The user's favourite drink is espresso", "preference")
        self.mem.remember("The user's sister is called Ana", "family")
        dup = self.mem.remember("the user's sister is called ana")
        self.assertEqual(len(self.mem.list_memories()), 2)
        hits = self.mem.search("what is my sister called?")
        self.assertEqual(hits[0]["text"], "The user's sister is called Ana")
        self.assertEqual(dup, hits[0]["id"])
        self.assertTrue(self.mem.forget(hits[0]["id"]))

    def test_todos_and_reminders(self):
        a = self.mem.add_todo("buy milk")
        self.mem.add_todo("file taxes", priority="high")
        self.assertEqual(self.mem.list_todos()[0]["text"], "file taxes")
        self.mem.complete_todo(a)
        self.assertEqual(len(self.mem.list_todos()), 1)
        rid = self.mem.add_reminder("stand up", time.time() - 1)
        fired = []
        sched = Scheduler(self.mem, on_fire=fired.append)
        import jarvis.platform_utils as pu
        original, pu.notify = pu.notify, lambda *a: None
        try:
            sched.check()
        finally:
            pu.notify = original
        self.assertEqual(fired, ["stand up"])
        self.assertFalse(self.mem.cancel_reminder(rid))


# ----------------------------------------------------------------- scheduler
class ParseWhenTests(unittest.TestCase):
    now = dt.datetime(2026, 3, 10, 14, 0)  # a Tuesday

    def test_relative(self):
        self.assertEqual(parse_when("in 10 minutes", self.now), self.now + dt.timedelta(minutes=10))
        self.assertEqual(parse_when("in an hour", self.now), self.now + dt.timedelta(hours=1))
        self.assertEqual(parse_when("2 hours 30 min", self.now), self.now + dt.timedelta(hours=2.5))
        self.assertEqual(parse_when("in half an hour", self.now), self.now + dt.timedelta(minutes=30))

    def test_absolute(self):
        self.assertEqual(parse_when("at 17:30", self.now), dt.datetime(2026, 3, 10, 17, 30))
        self.assertEqual(parse_when("9am", self.now), dt.datetime(2026, 3, 11, 9, 0))  # already past
        self.assertEqual(parse_when("tomorrow at 8pm", self.now), dt.datetime(2026, 3, 11, 20, 0))
        self.assertEqual(parse_when("friday 10:15", self.now), dt.datetime(2026, 3, 13, 10, 15))
        self.assertEqual(parse_when("2026-04-01 08:00", self.now), dt.datetime(2026, 4, 1, 8, 0))
        with self.assertRaises(ValueError):
            parse_when("whenever", self.now)


# ---------------------------------------------------------------- math/units
class MathTests(unittest.TestCase):
    def test_safe_eval(self):
        self.assertEqual(safe_eval("(15/100)*240"), 36)
        self.assertEqual(safe_eval("2^10"), 1024)
        self.assertAlmostEqual(safe_eval("sqrt(2)*sqrt(2)"), 2)
        self.assertEqual(safe_eval("mean([2, 4, 9])"), 5)
        for bad in ("__import__('os')", "open('x')", "().__class__", "9**999999"):
            with self.assertRaises(Exception):
                safe_eval(bad)

    def test_convert(self):
        self.assertAlmostEqual(convert(100, "C", "F"), 212)
        self.assertAlmostEqual(convert(1, "mile", "km"), 1.609344)
        self.assertAlmostEqual(convert(10, "lb", "kg"), 4.53592)
        with self.assertRaises(ValueError):
            convert(1, "kg", "km")


class SafetyTests(unittest.TestCase):
    def test_blocked_commands(self):
        for cmd in ("rm -rf /", "rm -rf ~", "mkfs.ext4 /dev/sda1", "format c:", "diskpart"):
            self.assertTrue(is_blocked(cmd), cmd)
        for cmd in ("ls -la", "git status", "rm -rf ./build", "Get-ChildItem"):
            self.assertFalse(is_blocked(cmd), cmd)


# ----------------------------------------------------------------- parsing
class ParsingTests(unittest.TestCase):
    def test_html_to_text(self):
        title, text = html_to_text("<html><head><title>T</title><style>x{}</style></head>"
                                   "<body><nav>menu</nav><p>Hello <b>world</b></p><script>bad()</script></body></html>")
        self.assertEqual(title, "T")
        self.assertIn("Hello world", text)
        self.assertNotIn("bad()", text)
        self.assertNotIn("menu", text)

    def test_ddg_results(self):
        markup = ('<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&amp;rut=x">'
                  'Example <b>A</b></a><a class="result__snippet" href="#">Snippet &amp; more</a>')
        self.assertEqual(_ddg_results(markup, 5),
                         [{"title": "Example A", "url": "https://example.com/a", "snippet": "Snippet & more"}])

    def test_rss_and_atom(self):
        rss = ("<rss><channel><item><title>One</title><link>https://a</link>"
               "<pubDate>Mon, 01 Jan 2026</pubDate></item></channel></rss>")
        atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Two</title>'
                '<link href="https://b"/><updated>2026-01-01</updated></entry></feed>')
        self.assertEqual(parse_feed(rss, 5)[0]["link"], "https://a")
        self.assertEqual(parse_feed(atom, 5)[0], {"title": "Two", "link": "https://b", "date": "2026-01-01"})


class VoiceTextTests(unittest.TestCase):
    def test_wake_word(self):
        self.assertEqual(match_wake_word("Jarvis, what's the weather?"), (True, "what's the weather?"))
        self.assertEqual(match_wake_word("Hey Jarvice open Safari"), (True, "open Safari"))
        self.assertEqual(match_wake_word("Jarvis."), (True, ""))
        self.assertEqual(match_wake_word("what is the time"), (False, ""))

    def test_clean_for_speech(self):
        self.assertEqual(clean_for_speech("**Done.** See https://x.y\n- item"), "Done. See a link item")


# -------------------------------------------------------------- orchestration
class OrchestrationTests(unittest.TestCase):
    def make(self, script, confirm=lambda p: True):
        cfg = Config.load()
        cfg.set("assistant.auto_memory", False)
        j = Jarvis(cfg, confirm=confirm, start_scheduler=False)
        llm = ScriptedLLM(cfg, script)
        j.llm = j.ctx.llm = llm
        j.memory.llm = None
        return j, llm

    def test_delegation_round_trip(self):
        script = [
            # JARVIS decides to delegate.
            LLMResponse("", [ToolCall("delegate", {"agent": "math", "task": "What is 15% of 240?"})]),
            # Math agent calls its tool, then reports.
            LLMResponse("", [ToolCall("calculate", {"expression": "0.15*240"})]),
            LLMResponse("15% of 240 is 36."),
            # JARVIS answers the user.
            LLMResponse("That would be 36, Sir."),
        ]
        j, llm = self.make(script)
        events = []
        j.on_event(lambda kind, data: events.append(kind))
        tokens = []
        reply = j.ask("What's 15 percent of 240?", on_token=tokens.append)
        self.assertEqual(reply, "That would be 36, Sir.")
        self.assertEqual("".join(tokens), "That would be 36, Sir.")
        self.assertEqual(events, ["agent_start", "tool", "tool_result", "agent_end"])
        math_tool_msg = llm.calls[2]["messages"][-1]
        self.assertEqual(math_tool_msg["role"], "tool")
        self.assertEqual(math_tool_msg["content"], "0.15*240 = 36")
        report = llm.calls[3]["messages"][-1]["content"]
        self.assertIn("15% of 240 is 36.", report)
        self.assertEqual(len(j.history), 2)
        j.shutdown()

    def test_parallel_delegation(self):
        script = [
            LLMResponse("", [ToolCall("delegate_parallel", {"tasks": [
                {"agent": "writer", "task": "Write a haiku"},
                {"agent": "translator", "task": "Translate hello to French"}]})]),
            LLMResponse("report"), LLMResponse("report"),
            LLMResponse("Both done."),
        ]
        j, llm = self.make(script)
        self.assertEqual(j.ask("do both"), "Both done.")
        self.assertEqual(llm.calls[-1]["messages"][-1]["content"].count("agent report"), 2)
        j.shutdown()

    def test_dangerous_tool_needs_approval(self):
        target = os.path.join(TMP, "keep.txt")
        open(target, "w").close()
        script = [
            LLMResponse("", [ToolCall("delegate", {"agent": "files", "task": f"delete {target}"})]),
            LLMResponse("", [ToolCall("delete_path", {"path": target})]),
            LLMResponse("The user declined."),
            LLMResponse("Understood, I left it alone."),
        ]
        asked = []
        j, llm = self.make(script, confirm=lambda p: asked.append(p) or False)
        j.ask("delete that file")
        self.assertTrue(os.path.exists(target))
        self.assertEqual(len(asked), 1)
        self.assertIn("declined", llm.calls[2]["messages"][-1]["content"])
        j.shutdown()

    def test_unknown_agent_is_reported(self):
        j, _ = self.make([])
        self.assertIn("No sub-agent named", j.core.delegate("nonexistent", "x"))
        j.shutdown()

    def test_memory_hint_injected(self):
        j, llm = self.make([LLMResponse("Ana, of course.")])
        j.memory.remember("The user's sister is called Ana")
        j.ask("what is my sister called")
        self.assertIn("sister is called Ana", llm.calls[0]["messages"][0]["content"])
        j.shutdown()

    def test_disabled_agents(self):
        cfg = Config.load()
        cfg.set("agents.disabled", ["shell", "code"])
        j = Jarvis(cfg, start_scheduler=False)
        self.assertNotIn("shell", j.agents)
        enum = j.core.get_tools()[0].parameters["properties"]["agent"]["enum"]
        self.assertNotIn("code", enum)
        j.shutdown()


# --------------------------------------------------------- HTTP client (fake)
class FakeOllama(BaseHTTPRequestHandler):
    requests: list = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"models": [{"name": "qwen2.5:7b"}]}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOllama.requests.append((self.path, payload))
        self.send_response(200)
        self.end_headers()
        if self.path == "/api/embed":
            self.wfile.write(json.dumps({"embeddings": [[1.0, 0.0]] * len(payload["input"])}).encode())
        elif payload.get("stream"):
            for chunk in ({"message": {"content": "Hel"}}, {"message": {"content": "lo"}},
                          {"message": {"content": "", "tool_calls": [
                              {"function": {"name": "calculate", "arguments": {"expression": "1+1"}}}]}},
                          {"done": True}):
                self.wfile.write(json.dumps(chunk).encode() + b"\n")
        else:
            self.wfile.write(json.dumps({"message": {"content": "<think>hmm</think>Hi there"}}).encode())


class OllamaClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cfg = Config.load()
        cfg.set("llm.base_url", f"http://127.0.0.1:{cls.httpd.server_address[1]}")
        cls.client = LLMClient(cfg)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def test_non_streaming_strips_thinking(self):
        resp = self.client.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(resp.content, "Hi there")
        path, payload = FakeOllama.requests[-1]
        self.assertEqual(path, "/api/chat")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["model"], "qwen2.5:7b")

    def test_streaming_with_tool_calls(self):
        tokens = []
        tools = [{"type": "function", "function": {"name": "calculate", "parameters": {}}}]
        msgs = [{"role": "assistant", "content": "", "tool_calls": [ToolCall("calculate", {"x": 1})]},
                {"role": "tool", "name": "calculate", "content": "2"}]
        resp = self.client.chat(msgs, tools=tools, on_token=tokens.append)
        self.assertEqual("".join(tokens), "Hello")
        self.assertEqual(resp.tool_calls[0].name, "calculate")
        sent = FakeOllama.requests[-1][1]["messages"]
        self.assertEqual(sent[0]["tool_calls"][0]["function"]["arguments"], {"x": 1})
        self.assertEqual(sent[1]["tool_name"], "calculate")

    def test_health_and_embed(self):
        self.assertTrue(self.client.health()[0])
        self.assertEqual(self.client.embed(["a", "b"]), [[1.0, 0.0], [1.0, 0.0]])

    def test_unreachable_server(self):
        cfg = Config.load()
        cfg.set("llm.base_url", "http://127.0.0.1:9")
        cfg.set("llm.timeout", 2)
        ok, detail = LLMClient(cfg).health()
        self.assertFalse(ok)
        self.assertIn("Ollama", detail)


# ------------------------------------------------------------------- server
class ServerTests(unittest.TestCase):
    def test_post_requires_header_and_local_host(self):
        import urllib.error
        import urllib.request
        from jarvis.server import App, make_handler
        app = App(Config.load())
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, check_host=True))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        try:
            req = urllib.request.Request(base + "/api/reset", data=b"{}", method="POST")
            with self.assertRaises(urllib.error.HTTPError) as err:
                urllib.request.urlopen(req)
            self.assertEqual(err.exception.code, 403)
            req = urllib.request.Request(base + "/api/reset", data=b"{}", method="POST",
                                         headers={"X-Jarvis": "1"})
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
            req = urllib.request.Request(base + "/", headers={"Host": "evil.example"})
            with self.assertRaises(urllib.error.HTTPError) as err:
                urllib.request.urlopen(req)
            self.assertEqual(err.exception.code, 403)
            with urllib.request.urlopen(base + "/") as resp:
                html = resp.read().decode()
            self.assertIn("J.A.R.V.I.S", html)
        finally:
            httpd.shutdown()
            app.jarvis.shutdown()


class ContextTests(unittest.TestCase):
    def test_auto_approve(self):
        cfg = Config.load()
        ctx = Context(config=cfg, llm=None, memory=None, confirm=lambda p: False)
        self.assertFalse(ctx.approve("x"))
        cfg.set("safety.auto_approve", True)
        self.assertTrue(ctx.approve("x"))


if __name__ == "__main__":
    unittest.main()
