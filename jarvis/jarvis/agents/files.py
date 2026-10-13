"""File management. Deletions go to ~/.jarvis/trash so they can be undone."""
from __future__ import annotations

import datetime as dt
import fnmatch
import os
import shutil
import time
from pathlib import Path

from .. import platform_utils
from ..agent import Agent
from ..tools import tool

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "Library", "AppData",
             "$Recycle.Bin", ".cache", ".Trash", "System Volume Information"}
CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".heic", ".webp", ".bmp", ".svg", ".tiff"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".pages", ".epub"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".numbers", ".ods"},
    "Presentations": {".ppt", ".pptx", ".key", ".odp"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"},
    "Video": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".dmg", ".iso"},
    "Installers": {".exe", ".msi", ".pkg", ".appimage", ".deb"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".java", ".c", ".cpp", ".go", ".rs", ".sh"},
}


def resolve(path: str) -> Path:
    path = (path or "~").strip().strip('"')
    aliases = {"desktop": "~/Desktop", "downloads": "~/Downloads", "documents": "~/Documents",
               "home": "~", "pictures": "~/Pictures", "music": "~/Music", "videos": "~/Videos",
               "movies": "~/Movies"}
    path = aliases.get(path.lower(), path)
    return Path(os.path.expandvars(path)).expanduser().resolve()


def _size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class FilesAgent(Agent):
    name = "files"
    title = "Files"
    description = ("Find, list, read, create, move, copy, delete (to trash) and organise files "
                   "and folders on this computer.")
    instructions = ("You manage the user's files. Paths may use ~ and the aliases desktop, "
                    "downloads, documents. Confirm results by listing when useful.")

    @tool
    def list_directory(self, path: str = "~", show_hidden: bool = False) -> str:
        """List files and folders in a directory with sizes and dates.

        Args:
            path: Folder to list.
            show_hidden: Include hidden files.
        """
        root = resolve(path)
        if not root.is_dir():
            return f"Not a folder: {root}"
        rows = []
        for entry in sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith(".") and not show_hidden:
                continue
            try:
                st = entry.stat()
            except OSError:
                continue
            kind = "DIR " if entry.is_dir() else _size(st.st_size).rjust(7)
            rows.append(f"{kind}  {dt.datetime.fromtimestamp(st.st_mtime):%Y-%m-%d}  {entry.name}")
            if len(rows) >= 200:
                rows.append("... (truncated)")
                break
        return f"{root}\n" + ("\n".join(rows) or "(empty)")

    @tool
    def search_files(self, pattern: str, folder: str = "~", max_results: int = 25) -> str:
        """Find files whose name matches a pattern (e.g. '*.pdf', 'invoice', 'report*2024*').

        Args:
            pattern: Name fragment or wildcard pattern.
            folder: Where to start searching.
            max_results: Maximum number of matches.
        """
        root = resolve(folder)
        pat = pattern.lower()
        if not any(ch in pat for ch in "*?["):
            pat = f"*{pat}*"
        found, deadline = [], time.time() + 20
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames + dirnames:
                if fnmatch.fnmatch(name.lower(), pat):
                    found.append(str(Path(dirpath) / name))
                    if len(found) >= max_results:
                        return "\n".join(found)
            if time.time() > deadline:
                found.append("(search stopped after 20s; narrow the folder for more)")
                break
        return "\n".join(found) or f"No files matching '{pattern}' under {root}."

    @tool
    def read_file(self, path: str, max_chars: int = 8000) -> str:
        """Read a text file.

        Args:
            path: File to read.
            max_chars: Maximum characters to return.
        """
        p = resolve(path)
        text = p.read_text(encoding="utf-8", errors="replace")
        return text[:max_chars] + (f"\n...[{len(text) - max_chars} more chars]" if len(text) > max_chars else "")

    @tool
    def file_info(self, path: str) -> dict:
        """Get size, type and dates of a file or folder.

        Args:
            path: The file or folder.
        """
        p = resolve(path)
        st = p.stat()
        size = st.st_size
        if p.is_dir():
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        return {"path": str(p), "type": "folder" if p.is_dir() else (p.suffix or "file"),
                "size": _size(size), "modified": f"{dt.datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M}",
                "created": f"{dt.datetime.fromtimestamp(st.st_ctime):%Y-%m-%d %H:%M}"}

    @tool
    def write_file(self, path: str, content: str, append: bool = False) -> str:
        """Create or overwrite a text file (or append to it).

        Args:
            path: File to write.
            content: Text content.
            append: Append instead of overwriting.
        """
        p = resolve(path)
        if p.exists() and not append and not self.ctx.approve(f"Overwrite existing file {p}?"):
            return "User declined to overwrite the file."
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a" if append else "w", encoding="utf-8") as fh:
            fh.write(content)
        return f"{'Appended to' if append else 'Wrote'} {p} ({len(content)} chars)."

    @tool
    def create_folder(self, path: str) -> str:
        """Create a folder (and any missing parents).

        Args:
            path: Folder to create.
        """
        p = resolve(path)
        p.mkdir(parents=True, exist_ok=True)
        return f"Created {p}"

    @tool(dangerous=True)
    def move_path(self, source: str, destination: str) -> str:
        """Move or rename a file or folder.

        Args:
            source: Existing path.
            destination: New path or target folder.
        """
        src, dst = resolve(source), resolve(destination)
        return f"Moved to {shutil.move(str(src), str(dst))}"

    @tool
    def copy_path(self, source: str, destination: str) -> str:
        """Copy a file or folder.

        Args:
            source: Existing path.
            destination: New path or target folder.
        """
        src, dst = resolve(source), resolve(destination)
        if src.is_dir():
            target = dst / src.name if dst.is_dir() else dst
            shutil.copytree(src, target)
            return f"Copied folder to {target}"
        return f"Copied to {shutil.copy2(src, dst)}"

    @tool(dangerous=True)
    def delete_path(self, path: str) -> str:
        """Delete a file or folder by moving it to JARVIS's trash (recoverable).

        Args:
            path: What to delete.
        """
        p = resolve(path)
        if not p.exists():
            return f"{p} does not exist."
        if p == Path.home() or len(p.parts) <= 2:
            return f"Refusing to delete top-level path {p}."
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self.ctx.config.trash_dir / f"{stamp}_{p.name}"
        shutil.move(str(p), str(target))
        return f"Moved {p} to trash ({target}). It can be restored from there."

    @tool
    def open_file(self, path: str) -> str:
        """Open a file or folder with its default application.

        Args:
            path: File or folder to open.
        """
        p = resolve(path)
        if not p.exists():
            return f"{p} does not exist."
        platform_utils.open_path(str(p))
        return f"Opened {p}"

    @tool(dangerous=True)
    def organize_folder(self, path: str = "downloads") -> str:
        """Tidy a folder by moving files into subfolders by type (Images, Documents, ...).

        Args:
            path: Folder to organise.
        """
        root = resolve(path)
        moved: dict[str, int] = {}
        for entry in root.iterdir():
            if not entry.is_file() or entry.name.startswith("."):
                continue
            ext = entry.suffix.lower()
            category = next((c for c, exts in CATEGORIES.items() if ext in exts), "Other")
            dest = root / category
            dest.mkdir(exist_ok=True)
            target = dest / entry.name
            n = 1
            while target.exists():
                target = dest / f"{entry.stem} ({n}){entry.suffix}"
                n += 1
            shutil.move(str(entry), str(target))
            moved[category] = moved.get(category, 0) + 1
        if not moved:
            return f"Nothing to organise in {root}."
        return f"Organised {root}: " + ", ".join(f"{n} → {c}" for c, n in sorted(moved.items()))
