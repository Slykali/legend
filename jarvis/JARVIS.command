#!/usr/bin/env bash
# Double-click in Finder to open the JARVIS HUD.
HERE="$(cd "$(dirname "$0")" && pwd)"
if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  if [[ -d /Applications/Ollama.app ]]; then open -a Ollama; else (ollama serve >/dev/null 2>&1 &); fi
  sleep 3
fi
exec "$HERE/jarvis.sh" web
