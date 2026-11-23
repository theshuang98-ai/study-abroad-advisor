"""Extract text and source metadata from official university PDFs.

pypdf returns reading-order text only. Table rows and columns can be lost or
misaligned; this module flags the risk and never reconstructs tables.

chunk_id design (chunking itself is not implemented here):
    "<document_id>:p<page_number:02d>:c<chunk_index:02d>"
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pypdf import PdfReader

SOURCE_FIELDS = (
    "source_id",
    "university",
    "title",
    "url",
    "source_type",
    "language",
    "admission_cycle",
    "accessed_at",
    "published_at",
    "access_status",
    "notes",
)

REQUIRED_SOURCE_FIELDS = ("source_id", "title", "url")

_TABLE_CELL_SPLIT = re.compile(r"\s{2,}")

# pypdf flattens single-spaced table columns, so a repeated header line is the
# remaining deterministic signal that a table exists on the page.
_TABLE_HEADER_TOKENS = frozenset(
    {
        "no.",
        "school/department",
        "program",
        "remark",
        "remarks",
        "duration",
        "tuition",
        "csca",
        "test subjects",
    }
)


class PdfIngestionError(RuntimeError):
    """Raised when a PDF cannot be read or its text cannot be extracted."""


def _table_rows(text: str) -> list[str]:
    rows: list[str] = []
    for line in text.splitlines():
        cells = [cell for cell in _TABLE_CELL_SPLIT.split(line.strip()) if cell]
        if len(cells) >= 3:
            rows.append(line.strip())
    return rows


def _has_table_header(text: str) -> bool:
    for line in text.splitlines():
        lowered = line.lower()
        hits = sum(1 for token in _TABLE_HEADER_TOKENS if token in lowered)
        if hits >= 4:
            return True
    return False


def _page_issues(text: str) -> list[tuple[str, str]]:
    if not text.strip():
        return [("empty_or_image_only_text", "no extractable text; page may be scanned")]

    issues: list[tuple[str, str]] = []
    rows = _table_rows(text)
    header = _has_table_header(text)
    if rows:
        issues.append(("possible_table_row", f"{len(rows)} whitespace-aligned row(s)"))
    if header:
        issues.append(("table_header_detected", "column header line found"))
    if header or len(rows) >= 2:
        issues.append(("table_layout_risk", "table columns may be lost or misaligned"))
    return issues


def parse_pdf(pdf_path: str | Path, source: Mapping[str, Any]) -> dict[str, Any]:
    """Parse a PDF into a JSON-serializable document with per-page text and warnings."""
    missing = [field for field in REQUIRED_SOURCE_FIELDS if not source.get(field)]
    if missing:
        raise ValueError(f"source record is missing required field(s): {', '.join(missing)}")

    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise PdfIngestionError(f"cannot read PDF {path.name}: {exc}") from exc

    if reader.is_encrypted:
        raise PdfIngestionError(f"PDF is encrypted: {path.name}")

    try:
        pdf_pages = list(reader.pages)
    except Exception as exc:
        raise PdfIngestionError(f"cannot open pages of {path.name}: {exc}") from exc

    document: dict[str, Any] = {"document_id": str(source["source_id"])}
    document.update({field: source.get(field) for field in SOURCE_FIELDS})

    pages: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for page_number, page in enumerate(pdf_pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            raise PdfIngestionError(
                f"cannot extract text from {path.name} page {page_number}: {exc}"
            ) from exc

        issues = _page_issues(text)
        pages.append(
            {
                "page_number": page_number,
                "text": text,
                "char_count": len(text),
                "warnings": [code for code, _ in issues],
            }
        )
        warnings.extend(
            {"page_number": page_number, "code": code, "detail": detail}
            for code, detail in issues
        )

    document["page_count"] = len(pages)
    document["pages"] = pages
    document["warnings"] = warnings
    return document


def write_parsed_json(document: Mapping[str, Any], out_dir: str | Path) -> Path:
    """Write a parsed document to ``<out_dir>/<document_id>.json`` and return the path."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{document['document_id']}.json"
    target.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target
