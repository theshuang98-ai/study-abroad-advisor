"""Build candidate program records from official webpage tables.

Only tables with an explicit program-name header are used. Missing or
ambiguous layout is reported as a warning instead of guessed by column order.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

DROP_TAGS = ("script", "style", "noscript", "nav", "header", "footer", "form", "iframe", "svg")
NAME_HEADERS = {"programsmajors", "programname", "majors", "major"}
NO_HEADERS = {"no", "number"}


@dataclass(frozen=True, slots=True)
class ProgramCandidate:
    candidate_id: str
    source_id: str
    program_name: str
    text: str


@dataclass(frozen=True, slots=True)
class WebExtractionResult:
    candidates: tuple[ProgramCandidate, ...]
    warnings: tuple[str, ...]


def extract_program_candidates(
    html: str,
    source: Mapping[str, Any],
) -> WebExtractionResult:
    """Return one candidate per program row; never infer missing columns."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(DROP_TAGS):
        tag.decompose()

    tables = soup.find_all("table")
    if not tables:
        return WebExtractionResult((), ("no tables found",))

    source_id = str(source["source_id"])
    candidates: list[ProgramCandidate] = []
    warnings: list[str] = []

    for table_index, table in enumerate(tables, start=1):
        grid = _table_grid(table)
        header_index, name_index = _find_header(grid)
        if header_index is None or name_index is None:
            warnings.append(f"table {table_index}: no Programs/Majors header")
            continue
        headers = grid[header_index]
        no_index = next(
            (
                index
                for index, header in enumerate(headers)
                if _normalize(header) in NO_HEADERS
            ),
            None,
        )
        for row_offset, row in enumerate(grid[header_index + 1 :], start=1):
            program_name = _cell(row, name_index)
            if not program_name:
                warnings.append(f"table {table_index} row {row_offset}: missing program name")
                continue
            number = _cell(row, no_index) if no_index is not None else ""
            suffix = number or str(row_offset)
            candidates.append(
                ProgramCandidate(
                    candidate_id=f"{source_id}#r{suffix}",
                    source_id=source_id,
                    program_name=program_name,
                    text=_candidate_text(headers, row, source, source_id),
                )
            )

    return WebExtractionResult(tuple(candidates), tuple(warnings))


def _find_header(grid: list[list[str]]) -> tuple[int | None, int | None]:
    for row_index, row in enumerate(grid[:5]):
        for column_index, value in enumerate(row):
            if _normalize(value) in NAME_HEADERS:
                return row_index, column_index
    return None, None


def _table_grid(table: Tag) -> list[list[str]]:
    """Rebuild the table, copying rowspan/colspan values into covered cells."""
    rows = [row for row in table.find_all("tr") if row.find_parent("table") is table]
    occupied: dict[tuple[int, int], str] = {}
    grid: list[list[str]] = []

    for row_index, row in enumerate(rows):
        values: list[str] = []
        column = 0
        for cell in row.find_all(["td", "th"], recursive=False):
            while (row_index, column) in occupied:
                values.append(occupied[(row_index, column)])
                column += 1
            text = _clean(cell.get_text(" "))
            rowspan = _span(cell.get("rowspan"))
            colspan = _span(cell.get("colspan"))
            for width in range(colspan):
                values.append(text)
                for height in range(rowspan):
                    occupied[(row_index + height, column + width)] = text
            column += colspan
        while (row_index, column) in occupied:
            values.append(occupied[(row_index, column)])
            column += 1
        grid.append(values)

    return grid


def _candidate_text(
    headers: list[str],
    row: list[str],
    source: Mapping[str, Any],
    source_id: str,
) -> str:
    lines = [
        f"Source: {source.get('title') or source_id}",
        f"University: {source.get('university', '')}",
        f"Admission cycle: {source.get('admission_cycle', '')}",
        "Catalog row:",
    ]
    for index, header in enumerate(headers):
        value = _cell(row, index)
        if header and value:
            lines.append(f"{header}: {value}")
    return "\n".join(lines)


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index]


def _span(value: str | None) -> int:
    try:
        return max(1, int(value or 1))
    except ValueError:
        return 1


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _clean(value: str) -> str:
    return " ".join(value.split())
