import json
from pathlib import Path

import pytest

from study_abroad.source_snapshots import load_catalog_sources, validate_snapshot_coverage


def _manifest(tmp_path: Path, **overrides) -> Path:
    source = {
        "source_id": "nju_source",
        "url": "https://example.edu/nju",
        "snapshot_path": ".local/sources/nju.html",
        "university": "Nanjing University",
        "title": "NJU Guide",
        "accessed_at": "2026-11-23",
    }
    source.update(overrides)
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": [source]}), encoding="utf-8")
    return manifest


def _snapshot(
    tmp_path: Path,
    content: str = "<html><body><p>Tuition 21000</p></body></html>",
) -> None:
    target = tmp_path / ".local/sources/nju.html"
    target.parent.mkdir(parents=True)
    target.write_text(content, encoding="utf-8")


def test_load_catalog_sources_extracts_visible_text(tmp_path: Path) -> None:
    source_manifest = _manifest(tmp_path)
    _snapshot(
        tmp_path,
        "<html><body><script>hidden()</script><h1>NJU</h1><p>Tuition 21000</p></body></html>",
    )

    sources = load_catalog_sources(source_manifest, tmp_path)

    assert sources["nju_source"].url == "https://example.edu/nju"
    assert sources["nju_source"].university == "Nanjing University"
    assert sources["nju_source"].title == "NJU Guide"
    assert sources["nju_source"].accessed_at == "2026-11-23"
    assert "NJU" in sources["nju_source"].text
    assert "Tuition 21000" in sources["nju_source"].text
    assert "hidden" not in sources["nju_source"].text


def test_duplicate_source_ids_are_rejected(tmp_path: Path) -> None:
    source = {
        "source_id": "nju_source",
        "url": "https://example.edu/nju",
        "snapshot_path": ".local/sources/nju.html",
    }
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": [source, source]}), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate source_id"):
        load_catalog_sources(manifest, tmp_path)


def test_missing_snapshot_is_rejected(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)

    with pytest.raises(FileNotFoundError, match="snapshot not found"):
        load_catalog_sources(manifest, tmp_path)


def test_snapshot_path_cannot_escape_project_root(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, snapshot_path="../outside.html")

    with pytest.raises(ValueError, match="escapes project root"):
        load_catalog_sources(manifest, tmp_path)


def test_missing_required_source_id_is_rejected(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, source_id="")
    _snapshot(tmp_path)

    with pytest.raises(ValueError, match="source_id"):
        load_catalog_sources(manifest, tmp_path)


def test_snapshot_coverage_reports_missing_sources(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    _snapshot(tmp_path)
    sources = load_catalog_sources(manifest, tmp_path)

    validate_snapshot_coverage({"nju_source"}, sources)
    with pytest.raises(ValueError, match="missing source snapshots"):
        validate_snapshot_coverage({"nju_source", "other_source"}, sources)
