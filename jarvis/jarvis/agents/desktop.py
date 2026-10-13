"""Desktop helpers, screen/image vision and media control."""
from __future__ import annotations

import base64
import datetime as dt
import urllib.parse
from pathlib import Path

from .. import platform_utils as pu
from ..agent import Agent
from ..tools import tool


class DesktopAgent(Agent):
    name = "desktop"
    title = "Desktop"
    description = "Clipboard (read/write), screenshots and desktop notifications."
    instructions = "You handle the clipboard, screenshots and notifications."

    @tool
    def get_clipboard(self) -> str:
        """Read the current clipboard text."""
        text = pu.get_clipboard()
        return text[:6000] if text.strip() else "The clipboard is empty (or holds non-text data)."

    @tool
    def set_clipboard(self, text: str) -> str:
        """Copy text to the clipboard.

        Args:
            text: Text to copy.
        """
        pu.set_clipboard(text)
        return "Copied to clipboard."

    @tool
    def take_screenshot(self, path: str = "") -> str:
        """Capture the screen to a PNG file and return its path.

        Args:
            path: Optional destination; defaults to ~/.jarvis/screenshots.
        """
        if not path:
            folder = self.ctx.config.home / "screenshots"
            folder.mkdir(exist_ok=True)
            path = str(folder / f"screen-{dt.datetime.now():%Y%m%d-%H%M%S}.png")
        return f"Screenshot saved to {pu.screenshot(path)}"

    @tool
    def send_notification(self, title: str, message: str) -> str:
        """Show a desktop notification.

        Args:
            title: Notification title.
            message: Notification text.
        """
        pu.notify(title, message)
        return "Notification sent."


class VisionAgent(Agent):
    name = "vision"
    title = "Vision"
    description = ("Sees the screen or an image file using a local vision model: describe, "
                   "read text (OCR), explain errors on screen, answer questions about images.")
    instructions = "You answer questions about what is on the user's screen or in images."

    def _look(self, image_path: str, question: str) -> str:
        data = base64.b64encode(Path(image_path).expanduser().read_bytes()).decode()
        model = self.ctx.config.get("llm.vision_model")
        resp = self.ctx.llm.chat([{"role": "user", "content": question or "Describe this image in detail.",
                                   "images": [data]}], model=model, temperature=0.2)
        return resp.content

    @tool
    def look_at_screen(self, question: str = "Describe what is on the screen.") -> str:
        """Take a screenshot and ask the vision model about it.

        Args:
            question: What to find out about the screen.
        """
        folder = self.ctx.config.home / "screenshots"
        folder.mkdir(exist_ok=True)
        shot = pu.screenshot(str(folder / "latest.png"))
        try:
            from PIL import Image  # type: ignore
            img = Image.open(shot)
            img.thumbnail((1600, 1600))
            img.save(shot)
        except Exception:
            pass
        return self._look(shot, question)

    @tool
    def analyze_image(self, path: str, question: str = "Describe this image in detail.") -> str:
        """Ask the vision model about an image file.

        Args:
            path: Image file path.
            question: What to find out.
        """
        return self._look(path, question)


class MediaAgent(Agent):
    name = "media"
    title = "Media"
    description = "Music and media: play/pause, next/previous track, volume, play a song or artist."
    instructions = ("You control media playback. To play something specific, use play_music; "
                    "otherwise use media keys.")

    @tool
    def play_pause(self) -> str:
        """Toggle play/pause of the current media."""
        return pu.media_control("play_pause")

    @tool
    def next_track(self) -> str:
        """Skip to the next track."""
        return pu.media_control("next")

    @tool
    def previous_track(self) -> str:
        """Go back to the previous track."""
        return pu.media_control("previous")

    @tool
    def set_volume(self, level: int) -> str:
        """Set the system output volume.

        Args:
            level: Volume 0-100.
        """
        return pu.set_volume(level)

    @tool
    def play_music(self, query: str, service: str = "spotify") -> str:
        """Search and play music by song, artist, album or mood.

        Args:
            query: What to play.
            service: 'spotify' (desktop app) or 'youtube' (browser).
        """
        q = urllib.parse.quote(query)
        if service.lower().startswith("spot"):
            try:
                pu.open_url(f"spotify:search:{q}")
                return f"Opened Spotify search for '{query}'. Press play on the top result."
            except Exception:
                pass
        pu.open_url(f"https://music.youtube.com/search?q={q}")
        return f"Opened YouTube Music search for '{query}'."
