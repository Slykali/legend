"""Summarise and question local documents (txt, md, pdf, docx, code, csv, html)."""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

from ..agent import Agent
from ..memory import _words
from ..tools import tool
from .files import resolve
from .web import html_to_text

CHUNK = 3500


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PDF support needs pypdf: pip install pypdf") from exc
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if suffix == ".docx":
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        xml = re.sub(r"</w:p>", "\n", xml)
        return re.sub(r"<[^>]+>", "", xml)
    if suffix in (".html", ".htm"):
        return html_to_text(path.read_text(encoding="utf-8", errors="replace"))[1]
    if suffix == ".csv":
        rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8", errors="replace"))))
        return "\n".join(", ".join(r) for r in rows[:500])
    return path.read_text(encoding="utf-8", errors="replace")


def chunks(text: str, size: int = CHUNK) -> list[str]:
    paras, out, cur = re.split(r"\n\s*\n", text), [], ""
    for p in paras:
        if len(cur) + len(p) > size and cur:
            out.append(cur)
            cur = ""
        while len(p) > size:
            out.append(p[:size])
            p = p[size:]
        cur += p + "\n\n"
    if cur.strip():
        out.append(cur)
    return out


class DocumentsAgent(Agent):
    name = "documents"
    title = "Documents"
    description = "Reads, summarises and answers questions about local documents (PDF, Word, text, CSV, code)."
    instructions = "You analyse documents on the user's computer. Quote key figures exactly."

    def _load(self, path: str) -> tuple[Path, str]:
        p = resolve(path)
        if not p.is_file():
            raise FileNotFoundError(f"No file at {p}")
        text = extract_text(p).strip()
        if not text:
            raise ValueError("No readable text in the document (scanned PDFs need OCR).")
        return p, text

    @tool
    def summarize_document(self, path: str, focus: str = "") -> str:
        """Summarise a document of any length.

        Args:
            path: Document path.
            focus: Optional aspect to focus on.
        """
        p, text = self._load(path)
        parts = chunks(text)[:30]
        hint = f" Focus on: {focus}." if focus else ""
        if len(parts) == 1:
            return self.ctx.llm.complete(f"Summarise this document.{hint}\n\n{parts[0]}", model=self.model)
        partials = [self.ctx.llm.complete(f"Summarise this section in 3-6 bullet points.{hint}\n\n{c}",
                                          model=self.model, temperature=0.2) for c in parts]
        joined = "\n\n".join(partials)
        return self.ctx.llm.complete(
            f"These are section summaries of '{p.name}'. Write one coherent summary with the key "
            f"points.{hint}\n\n{joined}", model=self.model)

    @tool
    def ask_document(self, path: str, question: str) -> str:
        """Answer a question using a document's content.

        Args:
            path: Document path.
            question: The question.
        """
        p, text = self._load(path)
        parts = chunks(text, 2000)
        q = _words(question)
        ranked = sorted(parts, key=lambda c: len(q & _words(c)), reverse=True)[:4]
        context = "\n---\n".join(ranked)
        return self.ctx.llm.complete(
            f"Using only these excerpts from '{p.name}', answer: {question}\n"
            f"If the answer is not there, say so.\n\n{context}", model=self.model, temperature=0.1)

    @tool
    def document_stats(self, path: str) -> dict:
        """Word count, characters and a preview of a document.

        Args:
            path: Document path.
        """
        p, text = self._load(path)
        return {"file": str(p), "words": len(text.split()), "characters": len(text),
                "preview": text[:600]}
