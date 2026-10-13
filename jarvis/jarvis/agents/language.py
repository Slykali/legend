"""Language specialists: writing, translation and communications."""
from __future__ import annotations

import urllib.parse

from .. import platform_utils as pu
from ..agent import Agent
from ..tools import tool


class WriterAgent(Agent):
    name = "writer"
    title = "Writer"
    description = ("Drafts, rewrites, proofreads, shortens or changes the tone of text: essays, "
                   "posts, letters, speeches, stories, summaries of pasted text.")
    instructions = ("You are a world-class writer and editor. Return only the finished text "
                    "unless asked for commentary. Match the requested tone and length.")
    temperature = 0.7


class TranslatorAgent(Agent):
    name = "translator"
    title = "Translator"
    description = "Translates text between any languages, explains phrases, idioms and grammar."
    instructions = ("You are an expert translator. Preserve meaning, tone and formatting. "
                    "Return the translation first; add brief notes only if something is ambiguous.")
    temperature = 0.2


class CommsAgent(Agent):
    name = "comms"
    title = "Communications"
    description = ("Drafts emails and messages and opens them in the user's mail client ready to "
                   "send (never sends automatically).")
    instructions = ("You write clear, polite emails and messages. When the user wants an email "
                    "prepared, call draft_email so it opens in their mail app.")
    temperature = 0.5

    @tool
    def draft_email(self, to: str, subject: str, body: str) -> str:
        """Open a pre-filled email in the default mail app for the user to review and send.

        Args:
            to: Recipient address(es), comma separated. May be empty.
            subject: Subject line.
            body: Email body text.
        """
        query = urllib.parse.urlencode({"subject": subject, "body": body}, quote_via=urllib.parse.quote)
        pu.open_url(f"mailto:{urllib.parse.quote(to, safe='@,')}?{query}")
        return "Draft opened in the mail app. The user must press send."

    @tool
    def copy_message(self, text: str) -> str:
        """Copy a drafted message to the clipboard so the user can paste it into any app.

        Args:
            text: The message.
        """
        pu.set_clipboard(text)
        return "Message copied to the clipboard."
