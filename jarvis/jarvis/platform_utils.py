"""Cross-platform OS helpers for macOS, Windows (and Linux as a bonus).

Everything uses built-in OS tools (osascript, PowerShell, ...) so no extra
packages are required; optional packages (psutil, Pillow) are used when
installed for richer results.
"""
from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

SYSTEM = platform.system()
IS_MAC = SYSTEM == "Darwin"
IS_WINDOWS = SYSTEM == "Windows"
IS_LINUX = SYSTEM == "Linux"
OS_NAME = "macOS" if IS_MAC else "Windows" if IS_WINDOWS else SYSTEM

try:
    import psutil  # type: ignore
except ImportError:  # optional
    psutil = None

NO_WINDOW = 0x08000000 if IS_WINDOWS else 0  # CREATE_NO_WINDOW


def run(cmd: list[str] | str, timeout: float = 15, shell: bool = False,
        env: dict | None = None, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout,
                          env={**os.environ, **(env or {})}, input=input_text,
                          creationflags=NO_WINDOW)


def powershell(script: str, timeout: float = 20, env: dict | None = None) -> subprocess.CompletedProcess:
    exe = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
    return run([exe, "-NoProfile", "-NonInteractive", "-Command", script],
               timeout=timeout, env=env)


def osascript(script: str, timeout: float = 15) -> subprocess.CompletedProcess:
    return run(["osascript", "-e", script], timeout=timeout)


def _as_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ------------------------------------------------------------------ opening
def open_path(path: str) -> None:
    p = str(Path(path).expanduser())
    if IS_WINDOWS:
        os.startfile(p)  # type: ignore[attr-defined]
    elif IS_MAC:
        run(["open", p])
    else:
        run(["xdg-open", p])


def open_url(url: str) -> None:
    if IS_MAC and not url.startswith(("http://", "https://")):
        run(["open", url])  # custom schemes like spotify:
    elif IS_WINDOWS and not url.startswith(("http://", "https://")):
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        webbrowser.open(url)


def open_app(name: str) -> str:
    if IS_MAC:
        res = run(["open", "-a", name])
        if res.returncode != 0:
            return f"Could not open '{name}': {res.stderr.strip()}"
        return f"Opened {name}."
    if IS_WINDOWS:
        # Start-Process resolves App Paths (chrome, winword...) and .exe names.
        res = powershell("Start-Process -FilePath $env:JARVIS_APP", env={"JARVIS_APP": name})
        if res.returncode != 0:
            # Fall back to Start-menu search via shell:AppsFolder.
            res2 = powershell(
                "$a = Get-StartApps | Where-Object { $_.Name -like \"*$env:JARVIS_APP*\" } | "
                "Select-Object -First 1; if ($a) { Start-Process (\"shell:AppsFolder\\\" + $a.AppID); "
                "$a.Name } else { exit 1 }", env={"JARVIS_APP": name})
            if res2.returncode != 0:
                return f"Could not find an application called '{name}'."
            return f"Opened {res2.stdout.strip() or name}."
        return f"Opened {name}."
    exe = shutil.which(name.lower()) or shutil.which(name)
    if not exe:
        return f"Could not find '{name}' on PATH."
    subprocess.Popen([exe], start_new_session=True)
    return f"Opened {name}."


def close_app(name: str) -> str:
    if IS_MAC:
        res = osascript(f"quit app {_as_quote(name)}")
        return f"Closed {name}." if res.returncode == 0 else f"Could not close {name}: {res.stderr.strip()}"
    if psutil:
        killed = 0
        needle = name.lower().removesuffix(".exe")
        for proc in psutil.process_iter(["name"]):
            pname = (proc.info.get("name") or "").lower().removesuffix(".exe")
            if pname == needle or (len(needle) > 3 and needle in pname):
                try:
                    proc.terminate()
                    killed += 1
                except Exception:
                    pass
        return f"Closed {killed} process(es) matching '{name}'." if killed else f"No running app matches '{name}'."
    if IS_WINDOWS:
        exe = name if name.lower().endswith(".exe") else name + ".exe"
        res = run(["taskkill", "/IM", exe])
        return res.stdout.strip() or res.stderr.strip()
    res = run(["pkill", "-f", name])
    return f"Closed {name}." if res.returncode == 0 else f"No running app matches '{name}'."


# ------------------------------------------------------------ notifications
def notify(title: str, message: str) -> None:
    try:
        if IS_MAC:
            osascript(f"display notification {_as_quote(message)} with title {_as_quote(title)}")
        elif IS_WINDOWS:
            powershell(
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$n = New-Object System.Windows.Forms.NotifyIcon; "
                "$n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true; "
                "$n.ShowBalloonTip(10000, $env:J_TITLE, $env:J_MSG, 'Info'); Start-Sleep 6; $n.Dispose()",
                timeout=15, env={"J_TITLE": title, "J_MSG": message})
        elif shutil.which("notify-send"):
            run(["notify-send", title, message])
    except Exception:
        pass


# ---------------------------------------------------------------- clipboard
def get_clipboard() -> str:
    if IS_MAC:
        return run(["pbpaste"]).stdout
    if IS_WINDOWS:
        return powershell("Get-Clipboard -Raw").stdout.rstrip("\r\n")
    for cmd in (["wl-paste"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "-ob"]):
        if shutil.which(cmd[0]):
            return run(cmd).stdout
    raise RuntimeError("No clipboard tool found (install wl-clipboard or xclip).")


def set_clipboard(text: str) -> None:
    if IS_MAC:
        run(["pbcopy"], input_text=text)
    elif IS_WINDOWS:
        powershell("Set-Clipboard -Value $env:J_CLIP", env={"J_CLIP": text})
    else:
        for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-ib"]):
            if shutil.which(cmd[0]):
                run(cmd, input_text=text)
                return
        raise RuntimeError("No clipboard tool found (install wl-clipboard or xclip).")


# --------------------------------------------------------------- screenshot
def screenshot(path: str) -> str:
    out = str(Path(path).expanduser())
    try:
        from PIL import ImageGrab  # type: ignore
        ImageGrab.grab(all_screens=True).save(out)
        return out
    except Exception:
        pass
    if IS_MAC:
        run(["screencapture", "-x", out])
    elif IS_WINDOWS:
        powershell(
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
            "$b = [System.Windows.Forms.SystemInformation]::VirtualScreen; "
            "$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height; "
            "$g = [System.Drawing.Graphics]::FromImage($bmp); "
            "$g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size); "
            "$bmp.Save($env:J_OUT, [System.Drawing.Imaging.ImageFormat]::Png)",
            env={"J_OUT": out})
    elif shutil.which("gnome-screenshot"):
        run(["gnome-screenshot", "-f", out])
    elif shutil.which("scrot"):
        run(["scrot", out])
    if not Path(out).exists():
        raise RuntimeError("Screenshot failed (on macOS grant Screen Recording permission to your terminal).")
    return out


# ----------------------------------------------------------- volume & media
_VK = {"volume_up": 0xAF, "volume_down": 0xAE, "mute": 0xAD,
       "play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "stop": 0xB2}


def _win_key(vk: int, times: int = 1) -> None:
    import ctypes
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    for _ in range(times):
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)


def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    if IS_MAC:
        osascript(f"set volume output volume {level}")
    elif IS_WINDOWS:
        # Each volume key press moves 2%; go to zero then step up.
        _win_key(_VK["volume_down"], 50)
        _win_key(_VK["volume_up"], round(level / 2))
    elif shutil.which("pactl"):
        run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])
    elif shutil.which("amixer"):
        run(["amixer", "-q", "sset", "Master", f"{level}%"])
    else:
        return "No volume control available."
    return f"Volume set to {level}%."


def get_volume() -> str:
    if IS_MAC:
        return osascript("output volume of (get volume settings)").stdout.strip() + "%"
    return "unknown (reading volume is only supported on macOS)"


def toggle_mute() -> str:
    if IS_MAC:
        muted = osascript("output muted of (get volume settings)").stdout.strip() == "true"
        osascript(f"set volume output muted {'false' if muted else 'true'}")
        return "Unmuted." if muted else "Muted."
    if IS_WINDOWS:
        _win_key(_VK["mute"])
        return "Toggled mute."
    if shutil.which("pactl"):
        run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
        return "Toggled mute."
    return "No volume control available."


def media_control(action: str) -> str:
    action = action.lower()
    if action not in ("play_pause", "next", "previous", "stop"):
        return f"Unknown media action '{action}'."
    if IS_WINDOWS:
        _win_key(_VK[action])
        return f"Sent {action}."
    if IS_MAC:
        verb = {"play_pause": "playpause", "next": "next track",
                "previous": "previous track", "stop": "pause"}[action]
        for app in ("Spotify", "Music"):
            running = osascript(f'application "{app}" is running').stdout.strip() == "true"
            if running:
                osascript(f'tell application "{app}" to {verb}')
                return f"{app}: {verb}."
        return "Neither Spotify nor Music is running."
    if shutil.which("playerctl"):
        verb = {"play_pause": "play-pause", "next": "next", "previous": "previous", "stop": "stop"}[action]
        run(["playerctl", verb])
        return f"Sent {verb}."
    return "No media controller available (install playerctl)."


# --------------------------------------------------------------- the system
def lock_screen() -> str:
    if IS_MAC:
        res = osascript('tell application "System Events" to keystroke "q" '
                        'using {control down, command down}')
        if res.returncode != 0:
            run(["pmset", "displaysleepnow"])
    elif IS_WINDOWS:
        run(["rundll32.exe", "user32.dll,LockWorkStation"])
    else:
        run(["loginctl", "lock-session"])
    return "Screen locked."


def system_info() -> dict:
    info: dict = {
        "os": f"{OS_NAME} {platform.release()} ({platform.version()[:60]})",
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "python": sys.version.split()[0],
        "cpu_cores": os.cpu_count(),
    }
    total, used, free = shutil.disk_usage(Path.home().anchor or "/")
    info["disk"] = f"{used / 1e9:.0f} GB used of {total / 1e9:.0f} GB ({free / 1e9:.0f} GB free)"
    if psutil:
        info["cpu_percent"] = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        info["memory"] = f"{mem.used / 1e9:.1f} GB used of {mem.total / 1e9:.1f} GB ({mem.percent}%)"
        info["uptime_hours"] = round((__import__("time").time() - psutil.boot_time()) / 3600, 1)
        bat = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        if bat:
            info["battery"] = f"{bat.percent:.0f}% ({'charging' if bat.power_plugged else 'on battery'})"
    return info


def battery() -> str:
    if psutil and hasattr(psutil, "sensors_battery"):
        bat = psutil.sensors_battery()
        if bat:
            state = "charging" if bat.power_plugged else "on battery"
            mins = "" if bat.power_plugged or bat.secsleft < 0 else f", ~{bat.secsleft // 60} min left"
            return f"{bat.percent:.0f}% ({state}{mins})"
    if IS_MAC:
        return run(["pmset", "-g", "batt"]).stdout.strip()
    if IS_WINDOWS:
        out = powershell("(Get-CimInstance Win32_Battery).EstimatedChargeRemaining").stdout.strip()
        return f"{out}%" if out else "No battery detected."
    return "Battery information unavailable."


def top_processes(sort_by: str = "cpu", limit: int = 10) -> list[dict]:
    if not psutil:
        raise RuntimeError("Install psutil for process information: pip install psutil")
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        procs.append(p.info)
    psutil.cpu_percent(interval=0.2)
    key = "memory_percent" if sort_by.startswith("mem") else "cpu_percent"
    procs.sort(key=lambda p: p.get(key) or 0, reverse=True)
    return [{"pid": p["pid"], "name": p["name"], "cpu%": round(p.get("cpu_percent") or 0, 1),
             "mem%": round(p.get("memory_percent") or 0, 1)} for p in procs[:limit]]


def network_info() -> dict:
    info = {"hostname": socket.gethostname()}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # no packets sent for UDP connect
            info["local_ip"] = s.getsockname()[0]
    except OSError:
        info["local_ip"] = "offline"
    return info


def default_shell() -> str:
    return "PowerShell" if IS_WINDOWS else os.environ.get("SHELL", "/bin/sh")
