"""Command-line entry point.

    jarvis                 text chat in the terminal
    jarvis voice           hands-free voice mode with wake word
    jarvis web             holographic web HUD in your browser
    jarvis ask "..."       one-shot question
    jarvis agents          list sub-agents
    jarvis doctor          check your setup
    jarvis setup           create config and download the local models
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import threading

from . import __version__
from . import platform_utils as pu
from .config import Config, jarvis_home

if pu.IS_WINDOWS:
    os.system("")  # enable ANSI colours in the Windows console
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

CYAN, GOLD, DIM, GREEN, RED, BOLD, RESET = ("\033[96m", "\033[93m", "\033[2m", "\033[92m",
                                             "\033[91m", "\033[1m", "\033[0m")
YES_RE = re.compile(r"\b(yes|yeah|yep|sure|ok|okay|proceed|go ahead|do it|affirmative|confirm|approved?)\b", re.I)

BANNER = f"""{CYAN}
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝{RESET}
{DIM}  Just A Rather Very Intelligent System · local edition v{__version__}{RESET}
"""

print_lock = threading.Lock()


def out(text: str = "", end: str = "\n") -> None:
    with print_lock:
        print(text, end=end, flush=True)


def event_printer(kind: str, data: dict) -> None:
    if kind == "agent_start":
        out(f"{DIM}  ▶ {data['title']} agent: {data['task'][:110]}{RESET}")
    elif kind == "tool":
        args = json.dumps(data["args"], ensure_ascii=False)
        out(f"{DIM}    ⚙ {data['tool']} {args[:100]}{RESET}")
    elif kind == "agent_end":
        out(f"{DIM}  ✓ {data['title']} done ({data['seconds']}s){RESET}")
    elif kind == "reminder":
        out(f"\n{GOLD}⏰ Reminder: {data['message']}{RESET}")


def terminal_confirm(prompt: str) -> bool:
    with print_lock:
        print(f"\n{GOLD}⚠ {prompt}{RESET}")
        try:
            return input(f"{GOLD}  Allow? [y/N] {RESET}").strip().lower() in ("y", "yes")
        except EOFError:
            return False


def build(config: Config, **kwargs):
    from .orchestrator import Jarvis
    jarvis = Jarvis(config, **kwargs)
    jarvis.on_event(event_printer)
    return jarvis


def check_model_server(config: Config) -> bool:
    from .llm import LLMClient
    ok, detail = LLMClient(config).health()
    if not ok:
        out(f"{RED}✗ {detail}{RESET}")
        out(f"{DIM}  Run 'jarvis doctor' for help.{RESET}")
    return ok


# ------------------------------------------------------------------ chat
def cmd_chat(config: Config, args) -> None:
    out(BANNER)
    check_model_server(config)
    speaker = None
    jarvis = build(config, confirm=terminal_confirm)
    name, user = config.get("assistant.name"), config.get("assistant.user_name")
    out(f"{DIM}  {len(jarvis.agents)} sub-agents online. Type /help for commands.{RESET}\n")
    while True:
        try:
            text = input(f"{BOLD}{user} ›{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            out("\nGoodbye.")
            break
        if not text:
            continue
        if text.startswith("/"):
            cmd, _, rest = text[1:].partition(" ")
            if cmd in ("quit", "exit", "q"):
                break
            if cmd == "help":
                out("/agents  /memory  /forget <id>  /todos  /reminders  /reset  /speak  /quit")
            elif cmd == "agents":
                for a in jarvis.agents.values():
                    out(f"  {CYAN}{a.name:<11}{RESET} {a.description}")
            elif cmd == "memory":
                for m in jarvis.memory.list_memories():
                    out(f"  #{m['id']} [{m['category']}] {m['text']}")
            elif cmd == "forget" and rest.strip().isdigit():
                out("Forgotten." if jarvis.memory.forget(int(rest)) else "No such memory.")
            elif cmd == "todos":
                for t in jarvis.memory.list_todos():
                    out(f"  #{t['id']} {t['text']}" + (f"  (due {t['due']})" if t["due"] else ""))
            elif cmd == "reminders":
                from .scheduler import describe_due
                for r in jarvis.memory.pending_reminders():
                    out(f"  #{r['id']} {describe_due(r['due'])}: {r['message']}")
            elif cmd == "reset":
                jarvis.reset()
                out("Conversation cleared.")
            elif cmd == "speak":
                if speaker:
                    speaker.stop()
                    speaker = None
                    jarvis.ctx.speak = None
                    out("Spoken replies off.")
                else:
                    from .voice import Speaker
                    speaker = Speaker(config.get("voice.tts_rate"), config.get("voice.tts_voice"))
                    jarvis.ctx.speak = speaker.say
                    out("Spoken replies on.")
            else:
                out("Unknown command. /help lists commands.")
            continue
        out(f"{CYAN}{name} ›{RESET} ", end="")
        streamed = []

        def on_token(tok: str) -> None:
            streamed.append(tok)
            out(tok, end="")
        try:
            reply = jarvis.ask(text, on_token=on_token)
        except KeyboardInterrupt:
            out(f"\n{DIM}(interrupted){RESET}")
            continue
        if not streamed:
            out(reply, end="")
        out("\n")
        if speaker:
            speaker.say(reply)
    jarvis.shutdown()


def cmd_ask(config: Config, args) -> None:
    jarvis = build(config, confirm=terminal_confirm, start_scheduler=False)
    jarvis.ask(" ".join(args.question), on_token=lambda t: out(t, end=""))
    out()
    jarvis.shutdown()


# ----------------------------------------------------------------- voice
def cmd_voice(config: Config, args) -> None:
    from .voice import Speaker, match_wake_word, shared_listener

    out(BANNER)
    if not check_model_server(config):
        return
    speaker = Speaker(config.get("voice.tts_rate"), config.get("voice.tts_voice"))
    out(f"{DIM}  Loading speech recognition ({config.get('voice.stt_model')})…{RESET}")
    try:
        listener = shared_listener(config.get("voice.stt_model"), config.get("voice.stt_device"))
    except RuntimeError as exc:
        out(f"{RED}✗ {exc}{RESET}")
        return
    wake = config.get("voice.wake_word", "jarvis")
    user = config.get("assistant.user_name")

    def voice_confirm(prompt: str) -> bool:
        out(f"\n{GOLD}⚠ {prompt}{RESET}")
        speaker.say(f"{user}, I need your authorisation for that. Shall I proceed?", block=True)
        answer = listener.listen(start_timeout=8)
        out(f"{DIM}  heard: {answer!r}{RESET}")
        return bool(YES_RE.search(answer or ""))

    jarvis = build(config, confirm=voice_confirm, speak=speaker.say)
    always = args.no_wake
    hint = "Just talk." if always else f"Say '{wake.title()}' followed by your request."
    out(f"{GREEN}● Listening. {hint} Say 'goodbye {wake}' to exit. Ctrl+C to quit.{RESET}\n")
    speaker.say(f"{config.get('assistant.name')} online. All systems nominal, {user}.", block=True)

    try:
        while True:
            heard_text = listener.listen()
            if not heard_text:
                continue
            if always:
                command = heard_text
            else:
                woke, command = match_wake_word(heard_text, wake)
                if not woke:
                    out(f"{DIM}  (ignored: {heard_text}){RESET}")
                    continue
                if not command:
                    speaker.say(f"Yes, {user}?", block=True)
                    command = listener.listen(start_timeout=6)
            while command:
                out(f"{BOLD}{user} ›{RESET} {command}")
                if re.search(r"\b(goodbye|shut ?down|go to sleep|exit|that's all)\b", command, re.I):
                    speaker.say(f"Very good, {user}. Powering down.", block=True)
                    raise KeyboardInterrupt
                out(f"{CYAN}{config.get('assistant.name')} ›{RESET} ", end="")
                reply = jarvis.ask(command, on_token=lambda t: out(t, end=""))
                out("\n")
                speaker.say(reply, block=True)
                # Allow a follow-up without repeating the wake word.
                command = listener.listen(start_timeout=float(config.get("voice.follow_up_seconds", 8)))
    except KeyboardInterrupt:
        out("\nGoodbye.")
    finally:
        speaker.stop()
        jarvis.shutdown()


# ------------------------------------------------------------------- web
def cmd_web(config: Config, args) -> None:
    from .server import serve
    out(BANNER)
    check_model_server(config)
    if args.port:
        config.set("server.port", args.port)
    serve(config, open_browser=not args.no_browser)


# ---------------------------------------------------------------- agents
def cmd_agents(config: Config, args) -> None:
    from .orchestrator import Jarvis
    jarvis = Jarvis(config, start_scheduler=False)
    out(f"{BOLD}{len(jarvis.agents)} sub-agents{RESET} (disable any via [agents] disabled = [...])\n")
    for a in jarvis.agents.values():
        tools = ", ".join(t.name for t in a.get_tools()) or "(pure language model)"
        out(f"{CYAN}{a.name:<11}{RESET}{a.description}\n{DIM}{'':<11}tools: {tools}{RESET}")


# ---------------------------------------------------------------- doctor
def cmd_doctor(config: Config, args) -> None:
    from .llm import LLMClient
    ok_mark, bad_mark, opt_mark = f"{GREEN}✓{RESET}", f"{RED}✗{RESET}", f"{GOLD}○{RESET}"
    out(f"{BOLD}JARVIS doctor{RESET}  ({pu.OS_NAME}, Python {sys.version.split()[0]})")
    out(f"  config: {config.path} {'(exists)' if config.path and config.path.exists() else '(using defaults)'}")
    out(f"  data:   {jarvis_home()}")
    if sys.version_info < (3, 11):
        out(f"  {bad_mark} Python 3.11+ is required")

    llm = LLMClient(config)
    ok, detail = llm.health()
    out(f"  {ok_mark if ok else bad_mark} {config.get('llm.provider')} at {config.get('llm.base_url')}: {detail}")
    if not ok and config.get("llm.provider") == "ollama":
        out(f"      Install Ollama from https://ollama.com/download and run 'ollama serve'.")
    if ok:
        have = llm.list_models()
        base = lambda n: n.split(":")[0]  # noqa: E731
        for key, needed in (("llm.model", True), ("llm.agent_model", False),
                            ("llm.embed_model", False), ("llm.vision_model", False)):
            name = config.get(key)
            if not name:
                continue
            present = name in have or f"{name}:latest" in have or (
                ":" not in name and any(base(h) == name for h in have))
            mark = ok_mark if present else (bad_mark if needed else opt_mark)
            tip = "" if present else f"  → ollama pull {name}"
            out(f"  {mark} {key} = {name}{tip}")

    for mod, purpose in (("psutil", "CPU/RAM/process info"), ("faster_whisper", "voice input"),
                         ("sounddevice", "microphone"), ("numpy", "voice input"),
                         ("PIL", "fast screenshots"), ("pypdf", "PDF documents")):
        present = importlib.util.find_spec(mod) is not None
        out(f"  {ok_mark if present else opt_mark} {mod:<15} {purpose}")
    tts = "say" if pu.IS_MAC else "powershell" if pu.IS_WINDOWS else (
        shutil.which("espeak-ng") or shutil.which("espeak") or shutil.which("spd-say"))
    out(f"  {ok_mark if tts and shutil.which(tts) else opt_mark} text-to-speech ({tts or 'install espeak-ng'})")


# ----------------------------------------------------------------- setup
def cmd_setup(config: Config, args) -> None:
    from pathlib import Path
    target = jarvis_home() / "config.toml"
    if not target.exists():
        example = Path(__file__).resolve().parent / "config.example.toml"
        if example.exists():
            shutil.copy(example, target)
            out(f"{GREEN}✓{RESET} Created {target} — edit it to personalise JARVIS.")
    else:
        out(f"  Config already exists at {target}")
    config = Config.load(target)
    if config.get("llm.provider") != "ollama":
        out("  Provider is not Ollama; load your models in your local server instead.")
        return
    from .llm import LLMClient, LLMError
    llm = LLMClient(config)
    models = [config.get(k) for k in ("llm.model", "llm.agent_model", "llm.embed_model")]
    if args.vision:
        models.append(config.get("llm.vision_model"))
    for model in dict.fromkeys(m for m in models if m):
        out(f"{CYAN}↓ Pulling {model}{RESET}")
        try:
            with llm._request("/api/pull", {"model": model, "stream": True}, stream=True) as resp:
                last = ""
                for line in resp:
                    data = json.loads(line or b"{}")
                    if data.get("error"):
                        raise LLMError(data["error"])
                    status = data.get("status", "")
                    if data.get("total"):
                        pct = 100 * data.get("completed", 0) / data["total"]
                        status = f"{status} {pct:5.1f}%"
                    if status != last:
                        out(f"\r  {status:<60}", end="")
                        last = status
            out(f"\r  {GREEN}✓ {model} ready{' ' * 50}{RESET}")
        except LLMError as exc:
            out(f"\n  {RED}✗ {exc}{RESET}")
    out(f"\n{GREEN}Setup complete.{RESET} Start with: jarvis   (or 'jarvis web', 'jarvis voice')")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="jarvis", description="Local JARVIS personal AI.")
    parser.add_argument("--config", help="Path to config.toml")
    parser.add_argument("--model", help="Override the main model for this run")
    parser.add_argument("--version", action="version", version=f"jarvis {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("chat", help="Text chat in the terminal (default)")
    v = sub.add_parser("voice", help="Hands-free voice mode")
    v.add_argument("--no-wake", action="store_true", help="Respond to everything, no wake word")
    w = sub.add_parser("web", help="Open the web HUD")
    w.add_argument("--port", type=int)
    w.add_argument("--no-browser", action="store_true")
    a = sub.add_parser("ask", help="Ask one question and exit")
    a.add_argument("question", nargs="+")
    sub.add_parser("agents", help="List sub-agents and their tools")
    sub.add_parser("doctor", help="Diagnose your installation")
    s = sub.add_parser("setup", help="Create config and download models")
    s.add_argument("--vision", action="store_true", help="Also download the vision model")
    args = parser.parse_args(argv)

    config = Config.load(args.config)
    if args.model:
        config.set("llm.model", args.model)
    handlers = {None: cmd_chat, "chat": cmd_chat, "voice": cmd_voice, "web": cmd_web,
                "ask": cmd_ask, "agents": cmd_agents, "doctor": cmd_doctor, "setup": cmd_setup}
    handlers[args.command](config, args)


if __name__ == "__main__":
    main()
