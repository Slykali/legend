#!/usr/bin/env bash
# Launch JARVIS (macOS/Linux). Examples: ./jarvis.sh   ./jarvis.sh web   ./jarvis.sh voice
HERE="$(cd "$(dirname "$0")" && pwd)"
if [[ -x "$HERE/.venv/bin/python" ]]; then
  exec "$HERE/.venv/bin/python" -m jarvis "$@"
fi
cd "$HERE" && exec python3 -m jarvis "$@"
