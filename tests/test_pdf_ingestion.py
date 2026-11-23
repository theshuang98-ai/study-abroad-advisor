from __future__ import annotations

import json
from pathlib import Path

import pytest

from study_abroad.pdf_ingestion import PdfIngestionError, parse_pdf, write_parsed_json

SOURCE = {
    "source_id": "fdu_test_guide",
    "university": "Fudan University",
    "title": "Fudan Test Admission Guide",
    "url": "https://example.edu/fdu-test.pdf",
    "source_type": "official_pdf",
    "language": "en",
    "admission_cycle": "2027_entry",
    "accessed_at": "2026-11-18",
    "published_at": "2026-11-03",
    "access_status": "accessible",
    "notes": None,
}


def _content_stream(text: str) -> bytes:
    parts = []
    y = 720
    for line in text.splitlines():
        parts.append(b"BT /F1 12 Tf 72 %d Td (%s) Tj ET" % (y, line.encode("latin-1")))
        y -= 20
    return b"\n".join(parts)


def _write_pdf(path: Path, page_texts: list[str]) -> None:
    """Write a minimal valid multi-page PDF with Helvetica text, no external dependency."""
    count = len(page_texts)
    font_number = 3 + count
    content_start = font_number + 1
    kids = b" ".join(b"%d 0 R" % number for number in range(3, 3 + count))

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, count),
    ]
    for index in range(count):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (font_number, content_start + index)
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for text in page_texts:
        stream = _content_stream(text)
        objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"

    xref_offset = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_offset,
    )
    path.write_bytes(bytes(out))


def test_parse_pdf_preserves_source_fields_and_page_numbers(tmp_path: Path) -> None:
    pdf = tmp_path / "guide.pdf"
    _write_pdf(pdf, ["Fudan University 2027 Guide", "Tuition 50000 CNY per year"])

    document = parse_pdf(pdf, SOURCE)

    assert document["document_id"] == SOURCE["source_id"]
    for field in (
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
    ):
        assert document[field] == SOURCE[field]
    assert document["page_count"] == 2
    assert [page["page_number"] for page in document["pages"]] == [1, 2]
    assert "Fudan University 2027 Guide" in document["pages"][0]["text"]
    assert "50000" in document["pages"][1]["text"]
    assert document["warnings"] == []
    json.dumps(document)


def test_parse_pdf_is_stable_across_calls(tmp_path: Path) -> None:
    pdf = tmp_path / "catalog.pdf"
    _write_pdf(pdf, ["Program list", "Second page"])

    first = parse_pdf(pdf, SOURCE)
    second = parse_pdf(pdf, SOURCE)

    assert first["document_id"] == second["document_id"]
    assert first["pages"] == second["pages"]


def test_empty_page_is_flagged_and_kept(tmp_path: Path) -> None:
    pdf = tmp_path / "scan.pdf"
    _write_pdf(pdf, ["Cover page", ""])

    document = parse_pdf(pdf, SOURCE)

    assert document["page_count"] == 2
    assert document["pages"][1]["text"] == ""
    assert document["pages"][1]["warnings"] == ["empty_or_image_only_text"]
    assert [(item["page_number"], item["code"]) for item in document["warnings"]] == [
        (2, "empty_or_image_only_text")
    ]


def test_single_table_row_is_flagged_without_layout_risk(tmp_path: Path) -> None:
    pdf = tmp_path / "tuition.pdf"
    _write_pdf(pdf, ["Heading\nProgram  Duration  Tuition"])

    document = parse_pdf(pdf, SOURCE)

    codes = document["pages"][0]["warnings"]
    assert "possible_table_row" in codes
    assert "table_layout_risk" not in codes
    assert "Program  Duration  Tuition" in document["pages"][0]["text"]


def test_multiple_table_rows_raise_layout_risk(tmp_path: Path) -> None:
    pdf = tmp_path / "programs.pdf"
    _write_pdf(
        pdf,
        ["Program  Duration  Tuition\nComputer Science  4 years  50000"],
    )

    document = parse_pdf(pdf, SOURCE)

    assert document["pages"][0]["warnings"] == [
        "possible_table_row",
        "table_layout_risk",
    ]
    assert [item["code"] for item in document["warnings"]] == [
        "possible_table_row",
        "table_layout_risk",
    ]


def test_single_spaced_table_header_is_flagged(tmp_path: Path) -> None:
    pdf = tmp_path / "catalog.pdf"
    _write_pdf(
        pdf,
        [
            "No. School/Department Program Remark Duration of Study "
            "CSCA Test Subjects Tuition\n"
            "1 Department of Chinese Language 4 years 50000"
        ],
    )

    document = parse_pdf(pdf, SOURCE)

    codes = document["pages"][0]["warnings"]
    assert "table_header_detected" in codes
    assert "table_layout_risk" in codes


def test_invalid_pdf_raises_ingestion_error(tmp_path: Path) -> None:
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"not a pdf")

    with pytest.raises(PdfIngestionError):
        parse_pdf(pdf, SOURCE)


def test_missing_pdf_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_pdf(tmp_path / "missing.pdf", SOURCE)


def test_source_record_must_have_identity_fields(tmp_path: Path) -> None:
    pdf = tmp_path / "guide.pdf"
    _write_pdf(pdf, ["Text"])

    with pytest.raises(ValueError, match="source_id"):
        parse_pdf(pdf, {"title": "No source id"})


def test_write_parsed_json_round_trips(tmp_path: Path) -> None:
    pdf = tmp_path / "catalog.pdf"
    _write_pdf(pdf, ["Fudan catalog"])
    document = parse_pdf(pdf, SOURCE)

    target = write_parsed_json(document, tmp_path / "out")

    assert target == tmp_path / "out" / f"{SOURCE['source_id']}.json"
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["document_id"] == SOURCE["source_id"]
    assert loaded["pages"][0]["text"] == document["pages"][0]["text"]
