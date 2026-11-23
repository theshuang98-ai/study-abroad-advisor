"""Build reviewable program candidates from parsed Fudan PDF documents.

pypdf flattens table columns, so this module never maps cells to Program
fields. It groups catalog pages into numbered row blocks, keeps the raw text,
and carries the page's table-risk warnings forward for manual review.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_TABLE_WARNINGS = frozenset(
    {"table_header_detected", "table_layout_risk", "possible_table_row"}
)
_REQUIRED_DOCUMENT_FIELDS = (
    "document_id",
    "source_id",
    "university",
    "url",
    "admission_cycle",
)

# Row starts look like "12 Department of ..." or a lone "12" line. The number
# must be followed by an uppercase name or end the line, so values such as
# "4 years" and "23,000" are not mistaken for rows. Numbers must stay sequential.
_ROW_MARKER = re.compile(r"(?<!\S)(\d{1,3})(?:\s+(?=[A-Z])|\s*$)")
_NOTES_START = re.compile(r"^notes\s*:", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ProgramCandidate:
    """One raw, unreviewed program block taken from a catalog page."""

    candidate_id: str
    document_id: str
    source_id: str
    university: str
    source_url: str
    admission_cycle: str
    page_number: int
    row_number: int | None
    text: str
    warnings: tuple[str, ...]


def _row_blocks(text: str, page_number: int) -> list[tuple[int, str]]:
    """Split a catalog page by sequential row numbers; keep wrapped lines attached."""
    blocks: list[tuple[int, list[str]]] = []
    last_number: int | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _NOTES_START.match(line):
            break
        if not blocks and last_number is None and line == str(page_number):
            continue  # printed page number, not a program row

        boundaries: list[tuple[int, int]] = []
        for match in _ROW_MARKER.finditer(line):
            number = int(match.group(1))
            if last_number is not None and number != last_number + 1:
                continue
            boundaries.append((number, match.start()))
            last_number = number

        if not boundaries:
            if blocks:
                blocks[-1][1].append(line)
            continue

        prefix = line[: boundaries[0][1]].strip()
        if prefix and blocks:
            blocks[-1][1].append(prefix)

        for index, (number, start) in enumerate(boundaries):
            end = boundaries[index + 1][1] if index + 1 < len(boundaries) else len(line)
            blocks.append((number, [line[start:end].strip()]))

    return [(number, "\n".join(lines).strip()) for number, lines in blocks if lines]


def _candidate(
    document: Mapping[str, Any],
    page_number: int,
    row_number: int | None,
    text: str,
    warnings: tuple[str, ...],
) -> ProgramCandidate:
    document_id = str(document["document_id"])
    suffix = f"r{row_number:02d}" if row_number is not None else "full"
    return ProgramCandidate(
        candidate_id=f"{document_id}:p{page_number:02d}:{suffix}",
        document_id=document_id,
        source_id=str(document["source_id"]),
        university=str(document["university"]),
        source_url=str(document["url"]),
        admission_cycle=str(document["admission_cycle"]),
        page_number=page_number,
        row_number=row_number,
        text=text,
        warnings=warnings,
    )


def extract_program_candidates(document: Mapping[str, Any]) -> list[ProgramCandidate]:
    """Return raw catalog blocks; table pages without row numbers keep one coarse block."""
    missing = [field for field in _REQUIRED_DOCUMENT_FIELDS if not document.get(field)]
    if missing:
        raise ValueError(f"document is missing required field(s): {', '.join(missing)}")

    pages = document.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("document has no pages to extract")

    candidates: list[ProgramCandidate] = []
    for page in pages:
        warnings = tuple(page.get("warnings") or ())
        if not _TABLE_WARNINGS.intersection(warnings):
            continue

        text = str(page.get("text") or "")
        if not text.strip():
            continue

        page_number = int(page["page_number"])
        rows = _row_blocks(text, page_number)
        if rows:
            candidates.extend(
                _candidate(document, page_number, number, block, warnings)
                for number, block in rows
            )
        else:
            candidates.append(
                _candidate(
                    document,
                    page_number,
                    None,
                    text.strip(),
                    warnings + ("coarse_page_block",),
                )
            )

    return candidates
