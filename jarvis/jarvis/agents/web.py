"""Web search, page reading and multi-source research."""
from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from .. import platform_utils
from ..agent import Agent
from ..tools import tool

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def http_get(url: str, timeout: float = 20, max_bytes: int = 3_000_000) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        raw = resp.read(max_bytes)
        charset = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, errors="replace"), ctype


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form", "aside", "iframe"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self.skip_depth:
            self.parts.append(data)


def html_to_text(markup: str) -> tuple[str, str]:
    parser = _TextExtractor()
    parser.feed(markup)
    text = "".join(parser.parts)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if len(ln) > 1]
    return parser.title.strip(), "\n".join(lines)


def _ddg_results(markup: str, limit: int) -> list[dict]:
    results = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)'
                         r'(?=<a[^>]+class="result__a"|$)', markup, re.S):
        href, title, rest = m.groups()
        q = urllib.parse.urlparse(html.unescape(href))
        url = urllib.parse.parse_qs(q.query).get("uddg", [html.unescape(href)])[0]
        if "duckduckgo.com/y.js" in url:
            continue  # ads
        snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', rest, re.S)
        clean = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()  # noqa: E731
        results.append({"title": clean(title), "url": url,
                        "snippet": clean(snip.group(1) if snip else "")})
        if len(results) >= limit:
            break
    return results


class WebAgent(Agent):
    name = "web"
    title = "Web"
    description = "Quick web searches, reading a specific web page, opening sites in the browser."
    instructions = ("You find information online. Search, then read the most promising page if "
                    "the snippets are not enough. Always include source URLs in your report.")

    @tool
    def web_search(self, query: str, max_results: int = 6) -> list[dict] | str:
        """Search the web and return titles, URLs and snippets.

        Args:
            query: What to search for.
            max_results: Number of results (1-10).
        """
        max_results = max(1, min(int(max_results), 10))
        searx = self.ctx.config.get("web.searxng_url")
        if searx:
            url = searx.rstrip("/") + "/search?" + urllib.parse.urlencode({"q": query, "format": "json"})
            import json
            data = json.loads(http_get(url)[0])
            return [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")}
                    for r in data.get("results", [])[:max_results]]
        body = urllib.parse.urlencode({"q": query})
        markup, _ = http_get("https://html.duckduckgo.com/html/?" + body)
        results = _ddg_results(markup, max_results)
        return results or "No results (the search engine may be rate limiting; try again shortly)."

    @tool
    def fetch_webpage(self, url: str, max_chars: int = 5000) -> str:
        """Download a web page and return its readable text.

        Args:
            url: Full URL starting with http(s)://
            max_chars: Maximum characters of text to return.
        """
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        markup, ctype = http_get(url)
        if "html" not in ctype and "<html" not in markup[:500].lower():
            return markup[:max_chars]
        title, text = html_to_text(markup)
        return f"TITLE: {title}\nURL: {url}\n\n{text[:int(max_chars)]}"

    @tool
    def open_in_browser(self, url: str) -> str:
        """Open a URL in the user's default web browser.

        Args:
            url: The address to open.
        """
        if not re.match(r"^[a-z]+:", url):
            url = "https://" + url
        platform_utils.open_url(url)
        return f"Opened {url}"


class ResearchAgent(WebAgent):
    name = "research"
    title = "Research"
    description = ("Deep multi-source research: compares several sources and writes a cited "
                   "briefing. Use for questions needing thorough, up-to-date answers.")
    instructions = (
        "You are a meticulous research analyst. Plan 2-4 different search queries, run them, "
        "read at least 2-4 of the best sources with fetch_webpage, cross-check facts, then write a "
        "structured briefing: a short answer first, then key findings as bullet points, then a "
        "'Sources' list of URLs you actually read. Note disagreements between sources.")
    max_steps = 14
    temperature = 0.2
