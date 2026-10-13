"""System control, shell commands and code execution."""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import platform_utils as pu
from ..agent import Agent
from ..tools import tool

# Commands that are refused even if the user approves them.
BLOCKED = [
    r"\brm\s+-[a-z]*r[a-z]*f?\s+(/|~|\$HOME|/\*)\s*$", r"\bmkfs\b", r"\bdd\s+.*of=/dev/",
    r"\bformat\s+[a-z]:", r"Remove-Item\s+.*-Recurse.*\s[A-Za-z]:\\?\s*$", r":\(\)\s*\{.*\};:",
    r"\bdel\s+/[sq].*[a-z]:\\\s*$", r"\bdiskpart\b", r"\bbcdedit\b",
]


def is_blocked(command: str) -> bool:
    return any(re.search(p, command, re.I) for p in BLOCKED)


class SystemAgent(Agent):
    name = "system"
    title = "System"
    description = ("Computer status and control: CPU/RAM/disk/battery, running processes, "
                   "open or close applications, volume, lock screen, network info.")
    instructions = f"You monitor and control the user's {pu.OS_NAME} computer."

    @tool
    def get_system_info(self) -> dict:
        """Get OS, CPU, memory, disk, battery and uptime information."""
        return pu.system_info()

    @tool
    def list_processes(self, sort_by: str = "cpu", limit: int = 10) -> list[dict]:
        """List the top running processes.

        Args:
            sort_by: 'cpu' or 'memory'.
            limit: How many to show.
        """
        return pu.top_processes(sort_by, int(limit))

    @tool
    def open_application(self, name: str) -> str:
        """Launch an application by name (e.g. 'Safari', 'Spotify', 'notepad', 'Visual Studio Code').

        Args:
            name: Application name.
        """
        return pu.open_app(name)

    @tool(dangerous=True)
    def close_application(self, name: str) -> str:
        """Quit a running application.

        Args:
            name: Application or process name.
        """
        return pu.close_app(name)

    @tool
    def set_volume(self, level: int) -> str:
        """Set the system output volume.

        Args:
            level: Volume from 0 to 100.
        """
        return pu.set_volume(level)

    @tool
    def toggle_mute(self) -> str:
        """Mute or unmute system audio."""
        return pu.toggle_mute()

    @tool
    def get_battery(self) -> str:
        """Get battery level and charging state."""
        return pu.battery()

    @tool
    def get_network_info(self) -> dict:
        """Get hostname and local IP address."""
        return pu.network_info()

    @tool(dangerous=True)
    def lock_screen(self) -> str:
        """Lock the computer screen."""
        return pu.lock_screen()


class ShellAgent(Agent):
    name = "shell"
    title = "Shell"
    description = ("Runs terminal/shell commands for anything not covered by another agent "
                   "(git, package managers, system utilities). Every command needs user approval.")
    instructions = (f"You operate the terminal. Commands run in {pu.default_shell()} on {pu.OS_NAME}. "
                    "Prefer safe, read-only commands; explain the output briefly.")

    @tool(dangerous=True)
    def run_command(self, command: str, working_directory: str = "~", timeout: int = 60) -> str:
        """Run a shell command and return its output.

        Args:
            command: The command line to run.
            working_directory: Folder to run it in.
            timeout: Seconds before the command is stopped.
        """
        if is_blocked(command):
            return "Refused: this command could destroy data or the operating system."
        cwd = Path(working_directory).expanduser()
        if pu.IS_WINDOWS:
            res = pu.powershell(f"Set-Location -LiteralPath $env:J_CWD; {command}",
                                timeout=int(timeout), env={"J_CWD": str(cwd)})
        else:
            shell = pu.default_shell()
            res = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True,
                                 timeout=int(timeout),
                                 executable=shell if Path(shell).exists() else None)
        out = (res.stdout or "") + (("\nSTDERR:\n" + res.stderr) if res.stderr.strip() else "")
        return f"exit code {res.returncode}\n{out.strip() or '(no output)'}"


class CodeAgent(Agent):
    name = "code"
    title = "Code"
    description = ("Writes, explains, debugs and runs code. Can execute Python for calculations, "
                   "data processing, file conversions or automation scripts.")
    instructions = ("You are a senior software engineer. Write clean, correct code. When running "
                    "code would answer the question, use run_python and print the result. Python "
                    "runs locally with the user's permissions; avoid destructive operations.")
    max_steps = 10
    temperature = 0.2

    @tool(dangerous=True)
    def run_python(self, code: str, timeout: int = 60) -> str:
        """Execute a Python script and return stdout/stderr. Use print() for output.

        Args:
            code: Complete Python source code.
            timeout: Seconds before the script is stopped.
        """
        workdir = self.ctx.config.workspace_dir
        with tempfile.NamedTemporaryFile("w", suffix=".py", dir=workdir, delete=False,
                                         encoding="utf-8") as fh:
            fh.write(code)
            script = fh.name
        try:
            res = subprocess.run([sys.executable, "-I", script], cwd=workdir, capture_output=True,
                                 text=True, timeout=int(timeout), creationflags=pu.NO_WINDOW)
        except subprocess.TimeoutExpired:
            return f"Timed out after {timeout}s."
        finally:
            Path(script).unlink(missing_ok=True)
        out = res.stdout + (("\nSTDERR:\n" + res.stderr) if res.stderr else "")
        return f"exit code {res.returncode}\n{out.strip() or '(no output)'}"

    @tool(dangerous=True)
    def save_code(self, path: str, code: str) -> str:
        """Save code to a file.

        Args:
            path: Destination file path.
            code: Source code.
        """
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.ctx.config.workspace_dir / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(code, encoding="utf-8")
        return f"Saved {p}"
