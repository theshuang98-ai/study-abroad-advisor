from __future__ import annotations

import json
from pathlib import Path

import pytest

from study_abroad.ingestion import (
    ingest_documents,
    load_sources,
    parse_source_file,
    parse_web_file,
)


def _source(source_id: str = "web_test", source_type: str = "official_webpage") -> dict:
    return {
        "source_id": source_id,
        "university": "Test University",
        "title": "2027 Test Guide",
        "url": "https://example.edu/guide",
        "source_type": source_type,
        "language": "en",
        "admission_cycle": "2027_entry",
        "accessed_at": "2026-11-19",
        "published_at": "2026-11-01",
        "access_status": "accessible",
        "notes": "test source",
    }


def test_parse_web_file_preserves_manifest_and_sections(tmp_path: Path) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text(
        """
        <html><body><nav>Navigation</nav><div class="wp_articlecontent">
        <h1>Admission Guide</h1><p>Applicants need a high school diploma.</p>
        <h2>Fees</h2><p>Tuition is 26,000 CNY per year.</p>
        </div></body></html>
        """,
        encoding="utf-8",
    )

    document = parse_web_file(html_path, _source())

    assert document["document_id"] == "web_test"
    assert document["source_type"] == "official_webpage"
    assert document["published_at"] == "2026-11-01"
    assert document["notes"] == "test source"
    assert document["sections"][0]["section_id"] == "web_test#s0"
    assert document["sections"][1]["heading"] == "Fees"
    assert "Admission Guide\nApplicants need" in document["text"]
    assert "Fees\nTuition is 26,000 CNY" in document["text"]
    assert "Navigation" not in document["text"]
    assert document["warnings"] == []
    json.dumps(document)


def test_parse_web_file_keeps_numbered_facts_in_empty_sections(tmp_path: Path) -> None:
    html_path = tmp_path / "fees.html"
    html_path.write_text(
        """
        <div class="wp_articlecontent">
        <p>IV. Fee Structure</p>
        <p>2. Tuition fee: RMB 9000 yuan/semester</p>
        </div>
        """,
        encoding="utf-8",
    )

    document = parse_web_file(html_path, _source())

    assert "IV. Fee Structure" in document["text"]
    assert "2. Tuition fee: RMB 9000 yuan/semester" in document["text"]


def test_ingest_documents_dispatches_and_writes(tmp_path: Path, monkeypatch) -> None:
    sources = [_source(), _source("pdf_test", "official_pdf")]
    html_path = tmp_path / "page.html"
    html_path.write_text(
        '<div class="wp_articlecontent"><p>Visible admission content for testing.</p></div>',
        encoding="utf-8",
    )
    pdf_path = tmp_path / "guide.pdf"
    pdf_path.write_bytes(b"placeholder")
    calls = []

    def fake_parse_pdf(path, source):
        calls.append((path, source["source_id"]))
        return {
            "document_id": source["source_id"],
            "source_id": source["source_id"],
            "title": source["title"],
            "url": source["url"],
            "source_type": source["source_type"],
            "language": source["language"],
            "admission_cycle": source["admission_cycle"],
            "accessed_at": source["accessed_at"],
            "published_at": source["published_at"],
            "access_status": source["access_status"],
            "notes": source["notes"],
            "page_count": 0,
            "pages": [],
            "warnings": [],
        }

    monkeypatch.setattr("study_abroad.ingestion.parse_pdf", fake_parse_pdf)

    paths = ingest_documents(
        sources,
        {"web_test": html_path, "pdf_test": pdf_path},
        tmp_path / "out",
    )

    assert calls == [(pdf_path, "pdf_test")]
    assert [path.name for path in paths] == ["web_test.json", "pdf_test.json"]
    web_output = json.loads(paths[0].read_text(encoding="utf-8"))
    pdf_output = json.loads(paths[1].read_text(encoding="utf-8"))
    assert "Visible admission content" in web_output["text"]
    assert pdf_output["page_count"] == 0


def test_ingest_documents_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(KeyError, match="web_test"):
        ingest_documents([_source()], {}, tmp_path / "out")


def test_parse_source_file_rejects_unknown_type(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported source_type"):
        parse_source_file(tmp_path / "input", _source(source_type="social_post"))


def test_load_sources_rejects_duplicate_ids(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": [_source(), _source()]}), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate source_id"):
        load_sources(manifest)
