"""Unified offline ingestion for official webpage and PDF sources."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from study_abroad.pdf_ingestion import parse_pdf, write_parsed_json
from study_abroad.web_ingestion import SourceMeta, WebDocument, parse_html


def _text_with_headings(document: WebDocument) -> str:
    """Keep headings because some numbered facts are parsed as empty sections."""
    lines: list[str] = []
    for section in document.sections:
        if section.heading:
            lines.append(section.heading)
        if section.text:
            lines.append(section.text)
    return "\n".join(lines)


def load_sources(manifest_path: str | Path) -> list[dict[str, Any]]:
    """Load source records and reject duplicate IDs before any parsing starts."""
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise ValueError("source manifest must contain a 'sources' array")

    source_ids = [str(source["source_id"]) for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source manifest contains duplicate source_id values")
    return sources


def parse_web_file(html_path: str | Path, source: Mapping[str, Any]) -> dict[str, Any]:
    """Parse one saved webpage and normalize it to the shared JSON shape."""
    html = Path(html_path).read_text(encoding="utf-8")
    document = parse_html(html, SourceMeta.from_manifest_entry(source))
    return {
        "document_id": document.document_id,
        "source_id": document.source_id,
        "university": document.university,
        "title": document.title,
        "url": document.url,
        "source_type": source.get("source_type"),
        "language": document.language,
        "admission_cycle": document.admission_cycle,
        "accessed_at": document.accessed_at,
        "published_at": source.get("published_at"),
        "access_status": source.get("access_status"),
        "notes": source.get("notes"),
        "sections": [asdict(section) for section in document.sections],
        "text": _text_with_headings(document),
        "warnings": [],
    }


def parse_source_file(path: str | Path, source: Mapping[str, Any]) -> dict[str, Any]:
    """Dispatch a local source file to the parser declared by its source type."""
    source_type = source.get("source_type")
    if source_type == "official_pdf":
        return parse_pdf(path, source)
    if source_type == "official_webpage":
        return parse_web_file(path, source)
    raise ValueError(f"unsupported source_type: {source_type!r}")


def ingest_documents(
    sources: Sequence[Mapping[str, Any]],
    inputs: Mapping[str, str | Path],
    out_dir: str | Path,
) -> list[Path]:
    """Parse every declared input and write local JSON artifacts.

    Missing inputs fail the whole run instead of silently producing partial coverage.
    """
    output_paths: list[Path] = []
    for source in sources:
        source_id = str(source["source_id"])
        if source_id not in inputs:
            raise KeyError(f"missing local input for source {source_id!r}")
        document = parse_source_file(inputs[source_id], source)
        output_paths.append(write_parsed_json(document, out_dir))
    return output_paths
