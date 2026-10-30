"""Turn untrusted job-description HTML into clean text before anything else sees it.

Hidden text and invisible Unicode are the usual carriers for prompt injection
aimed at AI agents, so both are stripped and flagged.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿\U000e0000-\U000e007f]")
HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d]*[1-9])|opacity\s*:\s*0(?![.\d]*[1-9])"
    r"|color\s*:\s*(?:#fff(?:fff)?|white|transparent)\b|height\s*:\s*0(?:px)?\s*;?\s*overflow\s*:\s*hidden",
    re.I,
)
INJECTION = re.compile(
    r"ignore (?:all |any )?(?:previous|prior|above) instructions|you are an ai|system prompt|"
    r"disregard (?:the )?(?:above|previous)|as an ai (?:model|assistant)",
    re.I,
)
VOID = {"br", "img", "hr", "input", "meta", "link", "area", "base", "col", "embed", "source", "wbr"}
BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "section"}
DROP = {"script", "style", "noscript", "template", "svg", "head", "title"}
MAX_CHARS = 20_000


@dataclass
class Sanitized:
    text: str
    flags: list[str] = field(default_factory=list)
    removed_hidden_chars: int = 0


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.hidden_out: list[str] = []
        # (tag, mode) where mode is "" (visible), "hidden" (styled away) or "drop" (script/style).
        self.stack: list[tuple[str, str]] = []

    def _mode(self) -> str:
        modes = {m for _, m in self.stack}
        return "drop" if "drop" in modes else ("hidden" if "hidden" in modes else "")

    def _hidden(self) -> bool:
        return self._mode() != ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in DROP:
            mode = "drop"
        elif (
            "hidden" in a
            or a.get("aria-hidden", "").lower() == "true"
            or bool(HIDDEN_STYLE.search(a.get("style", "")))
        ):
            mode = "hidden"
        else:
            mode = ""
        if tag in BLOCK and not self._hidden():
            self.out.append("\n")
            if tag == "li":
                self.out.append("- ")
        if tag not in VOID:
            self.stack.append((tag, mode))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in BLOCK and not self._hidden():
            self.out.append("\n")

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        if tag in BLOCK and not self._hidden():
            self.out.append("\n")

    def handle_data(self, data: str) -> None:
        mode = self._mode()
        if mode == "drop":
            return
        (self.hidden_out if mode == "hidden" else self.out).append(data)


def sanitize_html(raw: str | None) -> Sanitized:
    if not raw:
        return Sanitized(text="")
    text = raw
    if "&lt;" in text and "<" not in text:  # Greenhouse double-escapes its content
        text = html.unescape(text)
    flags: list[str] = []

    invisible = len(INVISIBLE.findall(text))
    if invisible:
        flags.append("invisible_unicode")
        text = INVISIBLE.sub("", text)

    parser = _Parser()
    parser.feed(text)
    parser.close()
    visible = "".join(parser.out)
    hidden = "".join(t for t in parser.hidden_out).strip()

    # Hidden text only counts if it is in the posting body (not scripts/styles).
    hidden_body = re.sub(r"\s+", " ", hidden)
    if len(hidden_body) > 20 or INJECTION.search(hidden_body):
        flags.append("hidden_text")
    if INJECTION.search(visible):
        flags.append("injection_phrase")

    visible = re.sub(r"[ \t\r\f\v]+", " ", visible)
    visible = re.sub(r" *\n *", "\n", visible)
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()
    if len(visible) > MAX_CHARS:
        visible = visible[:MAX_CHARS].rstrip() + " …"
        flags.append("truncated")
    return Sanitized(text=visible, flags=flags, removed_hidden_chars=len(hidden_body))


def sanitize_text(raw: str | None) -> Sanitized:
    """For plain-text descriptions: strip invisible characters and flag injection phrases."""
    if not raw:
        return Sanitized(text="")
    flags: list[str] = []
    if INVISIBLE.search(raw):
        flags.append("invisible_unicode")
    text = INVISIBLE.sub("", raw)
    if INJECTION.search(text):
        flags.append("injection_phrase")
    return Sanitized(text=text.strip()[:MAX_CHARS], flags=flags)
