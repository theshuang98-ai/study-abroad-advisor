"""Parse official university webpages into source-traceable text documents.

Raw HTML is stored under ``.local/sources/web/``. Parsing keeps only visible
content, preserves heading hierarchy, and never fills missing facts.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# First matching selector with real content wins; later ones are fallbacks.
CONTENT_SELECTORS = (
    ".wp_articlecontent",
    "#vsb_content",
    ".vsb_content",
    "article",
    "main",
    "[role=main]",
)
DROP_TAGS = ("script", "style", "noscript", "nav", "header", "footer", "form", "iframe", "svg")
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
BLOCK_TAGS = (*HEADING_TAGS, "p", "li", "tr")
MIN_CONTENT_CHARS = 50
# ZJU and XMU mark section headings as plain paragraphs such as "I. Eligibility".
NUMBERED_HEADING = re.compile(
    r"^(?:[IVXLC]+\.\s*|\d+(?:\.\d+)+\.?\s*|\d+\.\s*)[A-Z]"
)
MAX_NUMBERED_HEADING_CHARS = 120


@dataclass(frozen=True, slots=True)
class SourceMeta:
    """Identifying fields copied from ``data/source_manifest.json``."""

    source_id: str
    university: str
    title: str
    url: str
    language: str
    admission_cycle: str
    accessed_at: str

    @classmethod
    def from_manifest_entry(cls, entry: Mapping[str, Any]) -> SourceMeta:
        return cls(
            source_id=str(entry["source_id"]),
            university=str(entry["university"]),
            title=str(entry["title"]),
            url=str(entry["url"]),
            language=str(entry["language"]),
            admission_cycle=str(entry["admission_cycle"]),
            accessed_at=str(entry["accessed_at"]),
        )


@dataclass(frozen=True, slots=True)
class Section:
    """One heading-delimited block of page text."""

    section_id: str
    heading: str | None
    level: int | None
    text: str


@dataclass(frozen=True, slots=True)
class WebDocument:
    source_id: str
    document_id: str
    title: str
    url: str
    university: str
    language: str
    admission_cycle: str
    accessed_at: str
    text: str
    sections: tuple[Section, ...]


def fetch_html(
    url: str,
    *,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> str:
    """Download one page and decode it with the server-declared or detected encoding."""
    get = session.get if session is not None else requests.get
    response = get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    # requests falls back to ISO-8859-1 when the header has no charset (XMU).
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding
    return response.text


def parse_html(html: str, meta: SourceMeta) -> WebDocument:
    """Extract visible text and heading hierarchy from one official page."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(DROP_TAGS):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with(" ")

    root = _content_root(soup)
    sections: list[Section] = []
    heading: str | None = None
    level: int | None = None
    lines: list[str] = []

    def flush() -> None:
        text = "\n".join(lines)
        if text or heading is not None:
            sections.append(
                Section(
                    section_id=f"{meta.source_id}#s{len(sections)}",
                    heading=heading,
                    level=level,
                    text=text,
                )
            )
        lines.clear()

    for tag in root.find_all(BLOCK_TAGS):
        if tag.name == "p" and tag.find_parent(["li", "td", "th", "tr"]):
            continue
        line = _row_text(tag) if tag.name == "tr" else _clean(tag.get_text(""))
        if not line:
            continue
        numbered_level = _numbered_level(line) if tag.name == "p" else None
        if tag.name in HEADING_TAGS or numbered_level is not None:
            flush()
            heading = line
            level = int(tag.name[1]) if tag.name in HEADING_TAGS else numbered_level
            continue
        lines.append(line)

    flush()
    if not sections:
        raise ValueError(f"No extractable text for source {meta.source_id!r}")

    return WebDocument(
        source_id=meta.source_id,
        document_id=meta.source_id,
        title=meta.title,
        url=meta.url,
        university=meta.university,
        language=meta.language,
        admission_cycle=meta.admission_cycle,
        accessed_at=meta.accessed_at,
        text="\n".join(section.text for section in sections),
        sections=tuple(sections),
    )


def _content_root(soup: BeautifulSoup) -> Tag:
    for selector in CONTENT_SELECTORS:
        matches = [
            node
            for node in soup.select(selector)
            if len(_clean(node.get_text(""))) >= MIN_CONTENT_CHARS
        ]
        if matches:
            return max(matches, key=lambda node: len(_clean(node.get_text(""))))
    return soup.body or soup


def _numbered_level(text: str) -> int | None:
    if len(text) > MAX_NUMBERED_HEADING_CHARS or not NUMBERED_HEADING.match(text):
        return None
    if text[0] in "IVXLC":
        return 2
    match = re.match(r"^(\d+(?:\.\d+)*)", text)
    return 3 + match.group(1).count(".") if match else None


def _row_text(row: Tag) -> str:
    cells = [
        _clean(cell.get_text(""))
        for cell in row.find_all(["th", "td"], recursive=False)
    ]
    return " | ".join(cell for cell in cells if cell)


def _clean(text: str) -> str:
    return " ".join(text.split())
