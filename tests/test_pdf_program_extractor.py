from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from study_abroad.pdf_program_extractor import (
    ProgramCandidate,
    extract_program_candidates,
)

HEADER = (
    "No. School/Department Program Remark Duration of Study "
    "CSCA Test Subjects Tuition"
)
TABLE_WARNINGS = ["table_header_detected", "table_layout_risk"]


def _page(number: int, text: str, warnings: list[str] | None = None) -> dict:
    return {
        "page_number": number,
        "text": text,
        "char_count": len(text),
        "warnings": warnings or [],
    }


def _document(pages: list[dict], **overrides) -> dict:
    document = {
        "document_id": "fdu_2027_cn_undergraduate_catalog",
        "source_id": "fdu_2027_cn_undergraduate_catalog",
        "university": "Fudan University",
        "url": "https://example.edu/fdu-catalog.pdf",
        "admission_cycle": "2027_entry",
        "pages": pages,
        "warnings": [],
    }
    document.update(overrides)
    return document


def test_numbered_rows_become_individual_candidates() -> None:
    text = (
        f"{HEADER}\n"
        "1 Department of Chinese Language and\n"
        "Literature 4 years 50000\n"
        "2 Department of Tourism Tourism Management 4 years 50000"
    )
    document = _document([_page(1, text, TABLE_WARNINGS)])

    candidates = extract_program_candidates(document)

    assert [item.candidate_id for item in candidates] == [
        "fdu_2027_cn_undergraduate_catalog:p01:r01",
        "fdu_2027_cn_undergraduate_catalog:p01:r02",
    ]
    assert [item.row_number for item in candidates] == [1, 2]
    assert candidates[0].text.startswith("1 Department of Chinese Language")
    assert "Literature 4 years 50000" in candidates[0].text
    assert candidates[0].warnings == tuple(TABLE_WARNINGS)
    assert candidates[0].source_url == document["url"]
    assert candidates[0].university == "Fudan University"
    assert candidates[0].admission_cycle == "2027_entry"


def test_non_sequential_number_stays_in_previous_row() -> None:
    text = (
        "1 Department of X\n"
        "5 Unrelated continuation line\n"
        "2 Department of Y"
    )
    document = _document([_page(1, text, TABLE_WARNINGS)])

    candidates = extract_program_candidates(document)

    assert [item.row_number for item in candidates] == [1, 2]
    assert "5 Unrelated continuation line" in candidates[0].text


def test_table_page_without_row_numbers_keeps_one_coarse_block() -> None:
    text = f"{HEADER}\nDepartment information follows without row numbers."
    document = _document([_page(3, text, TABLE_WARNINGS)])

    candidates = extract_program_candidates(document)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.row_number is None
    assert candidate.candidate_id.endswith(":p03:full")
    assert "coarse_page_block" in candidate.warnings
    assert "Department information follows" in candidate.text


def test_non_table_pages_are_not_program_candidates() -> None:
    document = _document(
        [_page(1, "General admission requirements and deadlines.", [])]
    )

    assert extract_program_candidates(document) == []


def test_empty_table_page_is_skipped() -> None:
    document = _document([_page(1, "   ", TABLE_WARNINGS)])

    assert extract_program_candidates(document) == []


def test_lone_row_numbers_split_and_page_number_is_ignored() -> None:
    text = (
        "2 \n"
        f"{HEADER}\n"
        "19 Department of History History\n"
        "20 \n"
        "Department of Tourism Tourism Management"
    )
    document = _document([_page(2, text, TABLE_WARNINGS)])

    candidates = extract_program_candidates(document)

    assert [item.row_number for item in candidates] == [19, 20]
    assert candidates[0].text.startswith("19 Department of History")
    assert candidates[1].text.splitlines()[0] == "20"
    assert "Department of Tourism" in candidates[1].text


def test_inline_row_number_starts_a_new_candidate() -> None:
    text = f"{HEADER}\n50 School of Life Sciences Biological Sciences 51 Biotechnology"
    document = _document([_page(3, text, TABLE_WARNINGS)])

    candidates = extract_program_candidates(document)

    assert [item.row_number for item in candidates] == [50, 51]
    assert candidates[0].text == "50 School of Life Sciences Biological Sciences"
    assert candidates[1].text == "51 Biotechnology"


def test_trailing_notes_are_not_part_of_the_last_row() -> None:
    text = f"{HEADER}\n70 School of Stomatology Stomatology\nNotes:\n1. Students applying ..."
    document = _document([_page(4, text, TABLE_WARNINGS)])

    candidates = extract_program_candidates(document)

    assert len(candidates) == 1
    assert "Notes:" not in candidates[0].text


def test_candidates_are_stable_and_json_serializable() -> None:
    text = f"{HEADER}\n1 Department of X 4 years"
    document = _document([_page(1, text, TABLE_WARNINGS)])

    first = extract_program_candidates(document)
    second = extract_program_candidates(document)

    assert first == second
    payload = [asdict(item) for item in first]
    json.dumps(payload)


def test_document_metadata_is_required() -> None:
    document = _document([_page(1, f"{HEADER}\n1 Department of X")])
    document.pop("source_id")

    with pytest.raises(ValueError, match="source_id"):
        extract_program_candidates(document)


def test_document_must_have_pages() -> None:
    with pytest.raises(ValueError, match="no pages"):
        extract_program_candidates(_document([]))


def test_candidate_type_is_exposed() -> None:
    document = _document([_page(1, f"{HEADER}\n1 Department of X", TABLE_WARNINGS)])

    candidate = extract_program_candidates(document)[0]

    assert isinstance(candidate, ProgramCandidate)
