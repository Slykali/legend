#!/usr/bin/env bash
# JARVIS installer for macOS (also works on Linux).
# Usage:  ./install.sh            full install (voice, vision, docs extras)
#         ./install.sh --minimal  core only (no voice packages)
set -euo pipefail

cd "$(dirname "$0")"
HERE="$(pwd)"
CYAN='\033[96m'; GREEN='\033[92m'; GOLD='\033[93m'; RED='\033[91m'; RESET='\033[0m'
say() { printf "${CYAN}▶ %s${RESET}\n" "$1"; }
ok()  { printf "${GREEN}✓ %s${RESET}\n" "$1"; }
warn(){ printf "${GOLD}! %s${RESET}\n" "$1"; }
die() { printf "${RED}✗ %s${RESET}\n" "$1"; exit 1; }

MINIMAL=0
[[ "${1:-}" == "--minimal" ]] && MINIMAL=1

# ---------------------------------------------------------------- Python 3.11+
say "Checking Python"
PY=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && \
     "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$(command -v "$candidate")"; break
  fi
done
if [[ -z "$PY" ]]; then
  if [[ "$(uname)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
    say "Installing Python 3.12 with Homebrew"
    brew install python@3.12
    PY="$(brew --prefix)/bin/python3.12"
  else
    die "Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ and re-run."
  fi
fi
ok "Using $($PY --version) at $PY"

# ---------------------------------------------------------------- virtualenv
say "Creating virtual environment (.venv)"
"$PY" -m venv .venv
VPY="$HERE/.venv/bin/python"
"$VPY" -m pip install --quiet --upgrade pip
if [[ $MINIMAL -eq 1 ]]; then
  "$VPY" -m pip install --quiet -e ".[system,docs]"
else
  "$VPY" -m pip install --quiet -e ".[all]" || {
    warn "Some optional packages failed; installing the core with system extras only."
    "$VPY" -m pip install --quiet -e ".[system,docs]"
  }
fi
ok "Python packages installed"

# ---------------------------------------------------------------- Ollama
say "Checking Ollama (local model runtime)"
if ! command -v ollama >/dev/null 2>&1; then
  if [[ "$(uname)" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      brew install ollama
    else
      warn "Download Ollama for Mac from https://ollama.com/download, open it once, then re-run this script."
      open "https://ollama.com/download" || true
      exit 1
    fi
  else
    read -r -p "Ollama is not installed. Install it now with the official script? [Y/n] " answer
    [[ "${answer:-Y}" =~ ^[Yy]$ ]] || die "Ollama is required. See https://ollama.com/download"
    curl -fsSL https://ollama.com/install.sh | sh
  fi
fi
ok "Ollama installed"

if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  say "Starting the Ollama server"
  if [[ "$(uname)" == "Darwin" ]] && [[ -d "/Applications/Ollama.app" ]]; then
    open -a Ollama
  else
    nohup ollama serve >/dev/null 2>&1 &
  fi
  for _ in $(seq 1 30); do
    curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
  done
fi
curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1 || die "Ollama did not start. Run 'ollama serve' and re-run."
ok "Ollama is running"

# ---------------------------------------------------------------- models + config
say "Creating config and downloading models (several GB on first run)"
"$VPY" -m jarvis setup

# ---------------------------------------------------------------- launchers
chmod +x jarvis.sh JARVIS.command 2>/dev/null || true
ok "Installed!"
echo
printf "  ${CYAN}./jarvis.sh${RESET}          chat in the terminal\n"
printf "  ${CYAN}./jarvis.sh web${RESET}      holographic HUD in your browser\n"
printf "  ${CYAN}./jarvis.sh voice${RESET}    hands-free: say \"Jarvis, ...\"\n"
printf "  ${CYAN}./jarvis.sh doctor${RESET}   check everything\n"
if [[ "$(uname)" == "Darwin" ]]; then
  echo
  echo "  Or double-click JARVIS.command in Finder to open the HUD."
  echo "  macOS will ask for Microphone / Screen Recording / Automation permission the first"
  echo "  time JARVIS uses them; grant them to your Terminal app."
fi
