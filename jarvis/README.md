# J.A.R.V.I.S — local edition

A JARVIS-style personal AI that runs **entirely on your own Mac or Windows PC**. It uses a
local language model through [Ollama](https://ollama.com) (or any OpenAI-compatible local
server such as LM Studio), hands-free voice, a holographic web HUD, and a team of
**24 specialist sub-agents** directed by one orchestrator.

```
            ┌──────────────────────────── you ────────────────────────────┐
            │   terminal chat   ·   voice ("Jarvis, ...")   ·   web HUD   │
            └──────────────────────────────┬──────────────────────────────┘
                                           ▼
                         ┌───────────────────────────────────┐
                         │  JARVIS orchestrator (main model) │◄── long-term memory
                         │  delegate / delegate_parallel     │    (SQLite + embeddings)
                         └─────────────────┬─────────────────┘
       ┌──────────┬──────────┬─────────────┼─────────────┬───────────┬───────────┐
       ▼          ▼          ▼             ▼             ▼           ▼           ▼
    system      files      shell        research       tasks      vision      finance  …24
   (apps,     (search,   (commands,    (multi-source   (todos,    (screen,    (loans,
   volume)    organise)   approved)     web reports)  reminders)   images)    budgets)
```

## What it can do

| Area | Sub-agents | Examples |
|---|---|---|
| **Computer** | `system`, `files`, `shell`, `code`, `desktop` | "Open Spotify", "How's my battery?", "Find PDFs with 'invoice' in Downloads", "Organise my Downloads folder", "What's using all my CPU?", "Copy that to my clipboard" |
| **Knowledge** | `web`, `research`, `news`, `weather`, `briefing` | "Research the best budget 4K monitors, with sources", "Tech headlines", "Will it rain in Istanbul tomorrow?", "Good morning, Jarvis" |
| **Personal** | `memory`, `tasks`, `notes`, `planner` | "Remember my sister's birthday is 3 May", "Remind me to call mum at 6pm", "Start a 25 minute timer", "Plan a 3-day trip to Rome and save it as a note" |
| **Senses & media** | `vision`, `media`, `documents` | "What's this error on my screen?", "Next track", "Play some lo-fi", "Summarise ~/Documents/contract.pdf" |
| **Numbers** | `math`, `finance`, `fitness` | "What's 17.5% of 1,240?", "Monthly payment on a 250k mortgage at 4.5% over 25 years", "My BMI and daily calories: 80 kg, 180 cm, 30" |
| **Language** | `writer`, `translator`, `comms`, `tutor` | "Draft a polite email to my landlord about the heating", "Translate this to Turkish", "Explain transformers like I'm 12" |

JARVIS runs independent jobs **in parallel**. "What's the weather and the top news?" sends the
`weather` and `news` agents off at the same time. It also **remembers things about you**
on its own: personal facts you mention are stored locally and recalled when they're relevant.

Run `jarvis agents` to see every sub-agent and its tools (83 tools in total).

## Install

You need a reasonably modern computer. A 7–8B model needs about 8 GB of free RAM; Apple Silicon
Macs and PCs with an NVIDIA GPU are fastest.

### macOS

```bash
cd jarvis
./install.sh
```

The script installs Python 3.12 and Ollama with Homebrew if they're missing, creates a virtual
environment, installs the extras, starts Ollama and downloads the models. Afterwards you can
double-click **JARVIS.command** to open the HUD.

macOS asks for **Microphone**, **Screen Recording** (vision/screenshots) and **Automation**
(media/app control) permission the first time each one is used. Grant them to your terminal app.

### Windows 10/11

```powershell
cd jarvis
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

This installs Python and Ollama with `winget` if they're missing, sets everything up, and adds
a **JARVIS** shortcut to your desktop that opens the HUD.

### Manual install (any OS)

```bash
# 1. Install Ollama from https://ollama.com/download and start it
ollama pull qwen2.5:7b
ollama pull nomic-embed-text          # semantic memory (optional)
ollama pull llava:7b                  # vision agent (optional)

# 2. Install JARVIS (Python 3.11+)
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[all]"                               # or just: pip install -e .
jarvis setup
```

The core runs on the Python standard library alone. The extras add CPU/RAM stats (`psutil`),
voice input (`faster-whisper`, `sounddevice`), faster screenshots (`Pillow`) and PDF reading
(`pypdf`).

## Use

```bash
./jarvis.sh                 # chat in the terminal          (Windows: jarvis.bat)
./jarvis.sh web             # holographic HUD at http://127.0.0.1:8765
./jarvis.sh voice           # hands-free: "Jarvis, what's on my calendar?"
./jarvis.sh voice --no-wake # respond to everything you say, no wake word
./jarvis.sh ask "weather in Paris and top tech news"
./jarvis.sh agents          # list sub-agents and tools
./jarvis.sh doctor          # diagnose problems
./jarvis.sh --model llama3.1:8b   # try a different model for one run
```

**Terminal commands:** `/agents` `/memory` `/forget <id>` `/todos` `/reminders` `/reset`
`/speak` (read replies aloud) `/quit`

**Voice mode:** say *"Jarvis"* followed by your request. After it answers you can follow up
for a few seconds without repeating the wake word. Say *"goodbye Jarvis"* to exit.
Speech recognition is local Whisper. Speech output uses the voices built into your OS
(for a British butler, set `tts_voice = "Daniel"` on macOS or `"Microsoft George"` on Windows).

**Web HUD:** shows an animated arc reactor, the 24 sub-agents lighting up as they work, a
live log of every tool call, CPU/RAM meters, and a microphone button. Your audio is
transcribed locally on your machine. The VOICE button reads replies aloud.

## Choosing a model

The orchestrator needs a model that supports **tool calling**. Good options in Ollama:

| Your RAM | `model` | Notes |
|---|---|---|
| 8 GB | `qwen2.5:3b` or `llama3.2:3b` | fast, decent routing |
| 16 GB | `qwen2.5:7b` (default) or `llama3.1:8b` | good all-rounder |
| 32 GB+ | `qwen2.5:14b`, `qwen2.5:32b`, `mistral-small` | noticeably smarter |

Set `agent_model` to a smaller model (for example `qwen2.5:3b`) to make sub-agents faster
while the main model stays smart. When a model writes its tool calls as plain JSON text
instead of using the native format, JARVIS detects and runs them anyway.

**Using LM Studio / llama.cpp / Jan instead of Ollama:** set `provider = "openai"` and point
`base_url` at the server (LM Studio: `http://localhost:1234`).

## Configuration

`jarvis setup` creates `~/.jarvis/config.toml` (Windows: `C:\Users\<you>\.jarvis\config.toml`).
The full commented reference is in [`jarvis/config.example.toml`](jarvis/config.example.toml).
Common settings:

```toml
[assistant]
user_name = "Boss"

[llm]
model = "qwen2.5:7b"
agent_model = "qwen2.5:3b"

[weather]
default_location = "Istanbul"

[agents]
disabled = ["shell"]        # remove any sub-agents you don't want
```

Everything JARVIS stores lives in `~/.jarvis/`: memory database, notes (plain markdown),
screenshots, a scratch `workspace/` for code, and a `trash/` folder.

## Privacy & safety

- **Local by default.** The model, memory, notes, reminders and speech recognition all run on
  your machine. JARVIS only goes online when an agent needs to: web search (DuckDuckGo, or your
  own SearXNG), web pages, weather (Open-Meteo) and news (RSS).
- **You approve risky actions.** Shell commands, running code, moving or deleting files,
  closing apps and locking the screen all ask first, in the terminal, by voice ("yes/no") or
  with an on-screen dialog in the HUD. A few catastrophic commands (`rm -rf /`, `format c:`,
  `diskpart`…) are always refused.
- **Deletes are recoverable.** "Deleted" files go to `~/.jarvis/trash/`, not into oblivion.
- **Emails are never sent automatically.** The `comms` agent opens a ready-to-send draft in
  your mail app.
- The HUD listens on `127.0.0.1` only and rejects requests from other websites.

## Add your own sub-agent

Create a class, give it tools, and register it in `jarvis/agents/__init__.py`:

```python
from jarvis.agent import Agent
from jarvis.tools import tool

class HomeAgent(Agent):
    name = "home"
    title = "Home"
    description = "Controls the smart lights."   # the orchestrator reads this to pick agents
    instructions = "You control the user's smart home."

    @tool
    def set_lights(self, room: str, on: bool = True) -> str:
        """Turn a room's lights on or off.

        Args:
            room: Room name, e.g. 'kitchen'.
            on: True for on, False for off.
        """
        ...  # call your Home Assistant / Hue API here
        return f"{room} lights {'on' if on else 'off'}"

    @tool(dangerous=True)          # asks the user before running
    def unlock_door(self) -> str:
        """Unlock the front door."""
        ...
```

The type hints and docstring become the tool's JSON schema automatically.

## Troubleshooting

Run `./jarvis.sh doctor` first. It checks Python, the model server, each model and every
optional package, and tells you the exact fix.

- **"Cannot reach the local model server"**: start Ollama (`ollama serve`, or open the app).
- **It answers but never uses tools**: your model may not support tool calling; try `qwen2.5:7b` or `llama3.1:8b`.
- **Slow replies**: use a smaller `agent_model`, lower `num_ctx`, or a smaller main model.
- **Voice mode can't hear you (macOS)**: allow Microphone access for your terminal under System Settings → Privacy & Security.
- **Screenshots are black (macOS)**: allow Screen Recording for your terminal.
- **Search returns no results**: DuckDuckGo occasionally rate-limits; wait a minute, or set `web.searxng_url`.

## Development

```bash
python -m unittest discover -s tests     # 31 tests, no model needed
```

The project layout:

```
jarvis/
  cli.py            terminal chat, voice loop, doctor, setup
  orchestrator.py   JARVIS: memory recall, delegation, parallel sub-agents, auto-memory
  agent.py          Agent base class and the tool-calling loop
  llm.py            Ollama / OpenAI-compatible client, streaming, text tool-call fallback
  tools.py          @tool decorator → JSON schema
  memory.py         SQLite: memories (semantic search), messages, todos, reminders
  scheduler.py      reminder/timer thread and natural-language time parsing
  voice.py          Whisper speech-to-text, OS text-to-speech, wake word
  server.py         web HUD server (Server-Sent Events)
  platform_utils.py macOS / Windows / Linux system integration
  agents/           the 24 sub-agents
  web/index.html    the HUD
```
