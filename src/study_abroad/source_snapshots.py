"""Load versioned source snapshots for offline evidence validation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from bs4 import BeautifulSoup

from study_abroad.catalog_validation import CatalogSource

_REQUIRED_FIELDS = ("source_id", "url", "snapshot_path")


def load_catalog_sources(
    manifest_path: str | Path,
    project_root: str | Path,
) -> dict[str, CatalogSource]:
    """Load each declared HTML snapshot and return searchable visible text."""
    manifest_file = Path(manifest_path)
    payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    records = payload.get("sources")
    if not isinstance(records, list) or not records:
        raise ValueError("source manifest must contain a non-empty 'sources' array")

    root = Path(project_root).resolve()
    source_ids = [str(record["source_id"]) for record in records]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source manifest contains duplicate source_id values")

    result: dict[str, CatalogSource] = {}
    for record in records:
        missing = [field for field in _REQUIRED_FIELDS if not record.get(field)]
        if missing:
            raise ValueError(f"source record missing field(s): {', '.join(missing)}")

        snapshot = (root / str(record["snapshot_path"])).resolve()
        if not snapshot.is_relative_to(root):
            raise ValueError(f"snapshot path escapes project root: {record['snapshot_path']}")
        if not snapshot.is_file():
            raise FileNotFoundError(f"source snapshot not found: {record['snapshot_path']}")

        soup = BeautifulSoup(snapshot.read_bytes(), "html.parser")
        for tag in soup(("script", "style", "noscript")):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        if not text:
            raise ValueError(f"source snapshot has no visible text: {record['source_id']}")

        result[str(record["source_id"])] = CatalogSource(
            source_id=str(record["source_id"]),
            url=str(record["url"]),
            text=text,
            university=str(record.get("university") or ""),
            title=str(record.get("title") or ""),
            accessed_at=str(record.get("accessed_at") or ""),
        )
    return result


def validate_snapshot_coverage(
    required_source_ids: set[str],
    loaded_sources: Mapping[str, CatalogSource],
) -> None:
    """Fail when evidence refers to a source absent from the manifest."""
    missing = sorted(required_source_ids - set(loaded_sources))
    if missing:
        raise ValueError(f"missing source snapshots: {', '.join(missing)}")
