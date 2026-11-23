from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from study_abroad.chunking import (
    Chunk,
    ChunkingError,
    chunks_from_documents,
    chunks_from_programs,
    write_chunks_json,
)

NOW = datetime(2026, 11, 22, tzinfo=UTC)
SOURCE = {
    "document_id": "xmu_2027_undergraduate_guide",
    "source_id": "xmu_2027_undergraduate_guide",
    "university": "Xiamen University",
    "url": "https://admissions.xmu.edu.cn/Admissions/Undergraduate_Students.htm",
    "source_type": "official_webpage",
    "language": "en",
    "admission_cycle": "2027_entry",
    "accessed_at": "2026-11-19",
    "published_at": None,
    "access_status": "accessible",
    "notes": None,
    "sections": [
        {
            "section_id": "xmu_2027_undergraduate_guide#s0",
            "heading": "Fees",
            "level": 2,
            "text": "Tuition is RMB 26,000/year.",
        },
        {
            "section_id": "xmu_2027_undergraduate_guide#s1",
            "heading": "Timeline",
            "level": 2,
            "text": "The application deadline is May 31, 2027.",
        },
    ],
    "text": (
        "2027 Admission Guide of Xiamen University for Undergraduate Programs\n"
        "Tuition is RMB 26,000/year.\n"
        "The application deadline is May 31, 2027."
    ),
    "warnings": [],
}
PDF = {
    "document_id": "fdu_2027_cn_undergraduate_catalog",
    "source_id": "fdu_2027_cn_undergraduate_catalog",
    "university": "Fudan University",
    "url": "https://iso.fudan.edu.cn/catalog.pdf",
    "source_type": "official_pdf",
    "language": "en",
    "admission_cycle": "2027_entry",
    "accessed_at": "2026-11-18",
    "published_at": "2026-11-03",
    "access_status": "accessible",
    "notes": None,
    "page_count": 2,
    "pages": [
        {
            "page_number": 1,
            "text": (
                "Fudan University 2027 Chinese-taught Undergraduate Programs\n"
                "No. School/Department Program\n"
                "Fudan University 2027 Chinese-taught Undergraduate Programs"
            ),
            "char_count": 100,
            "warnings": [],
        },
        {
            "page_number": 2,
            "text": "Clinical Medicine (5 years)\n42,000 RMB/Year",
            "char_count": 50,
            "warnings": [],
        },
    ],
    "warnings": [],
}
PROGRAM = {
    "program_id": "xmu_computer_science_technology",
    "university": "Xiamen University",
    "program_name_original": "Computer Science and Technology",
    "degree_level": "bachelor",
    "is_degree_program": True,
    "academic_field": "Engineering",
    "instruction_languages": ["zh"],
    "duration_text": "4 years",
    "tuition_amount": 26000,
    "tuition_currency": "CNY",
    "tuition_period": "year",
    "tuition_text": "RMB 26,000/year",
    "application_deadline": "2027-05-31",
    "deadline_text": "May 31, 2027",
    "language_requirements": ["HSK 4 with 210 or better"],
    "academic_requirements": ["Senior high school diploma"],
    "admission_cycle": "2027_entry",
    "verification_status": "verified",
    "evidence": [
        {
            "source_id": "xmu_2027_undergraduate_guide",
            "field_name": "tuition_amount",
            "source_url": "https://admissions.xmu.edu.cn/Admissions/Undergraduate_Students.htm",
            "source_quote": "Tuition is RMB 26,000/year.",
            "admission_cycle": "2027_entry",
            "collected_at": NOW,
        }
    ],
    "collected_at": NOW,
}


def test_web_sections_produce_stable_chunk_ids_and_metadata() -> None:
    chunks = chunks_from_documents([SOURCE])

    assert len(chunks) == 2
    assert [chunk.chunk_id for chunk in chunks] == [
        "xmu_2027_undergraduate_guide#s0",
        "xmu_2027_undergraduate_guide#s1",
    ]
    assert all(chunk.document_id == "xmu_2027_undergraduate_guide" for chunk in chunks)
    assert all(chunk.university == "Xiamen University" for chunk in chunks)
    assert all(chunk.admission_cycle == "2027_entry" for chunk in chunks)
    assert all(chunk.source_url == SOURCE["url"] for chunk in chunks)
    assert "Tuition is RMB 26,000/year" in chunks[0].text
    assert "May 31, 2027" in chunks[1].text
    assert all(isinstance(chunk, Chunk) for chunk in chunks)


def test_pdf_pages_keep_page_numbers_and_empty_pages_are_skipped() -> None:
    document = dict(PDF)
    document["pages"] = [
        *PDF["pages"],
        {"page_number": 3, "text": "", "char_count": 0, "warnings": []},
    ]

    chunks = chunks_from_documents([document])

    assert [chunk.chunk_id for chunk in chunks] == [
        "fdu_2027_cn_undergraduate_catalog:p01",
        "fdu_2027_cn_undergraduate_catalog:p02",
    ]
    assert "Clinical Medicine" in chunks[1].text


def test_program_facts_create_one_chunk_with_source_quote() -> None:
    chunks = chunks_from_programs(
        [PROGRAM],
        {SOURCE["document_id"]: SOURCE},
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_id == "xmu_computer_science_technology#fact"
    assert chunk.program_id == "xmu_computer_science_technology"
    assert chunk.document_id == "xmu_2027_undergraduate_guide"
    assert chunk.source_quote == "Tuition is RMB 26,000/year."
    assert "Computer Science and Technology" in chunk.text


def test_empty_sections_are_skipped_and_non_empty_sections_produce_chunks() -> None:
    source = dict(SOURCE)
    source["title"] = ""
    source["sections"] = [
        {
            "section_id": "xmu_2027_undergraduate_guide#s0",
            "heading": "",
            "level": 2,
            "text": " ",
        },
        {
            "section_id": "xmu_2027_undergraduate_guide#s1",
            "heading": "Timeline",
            "level": 2,
            "text": "The application deadline is May 31, 2027.",
        },
    ]

    chunks = chunks_from_documents([source])

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "xmu_2027_undergraduate_guide#s1"
    assert chunks[0].source_quote == "The application deadline is May 31, 2027."



def test_heading_only_section_is_kept_as_a_fact_chunk() -> None:
    source = dict(SOURCE)
    source["sections"] = [
        {
            "section_id": "zju_fees#s4",
            "heading": "2. Tuition fee: RMB 9000 yuan/semester",
            "level": 3,
            "text": "",
        }
    ]

    chunks = chunks_from_documents([source])

    assert len(chunks) == 1
    assert chunks[0].text == "2. Tuition fee: RMB 9000 yuan/semester"
    assert chunks[0].source_quote == "2. Tuition fee: RMB 9000 yuan/semester"


def test_unknown_source_type_is_rejected() -> None:
    with pytest.raises(ChunkingError, match="unsupported source_type"):
        chunks_from_documents(
            [
                {
                    "source_type": "social_post",
                    "document_id": "x",
                    "university": "u",
                    "admission_cycle": "2027_entry",
                    "url": "https://example.edu",
                    "accessed_at": "2026-11-19",
                    "text": "x",
                }
            ]
        )


def test_write_chunks_json_round_trips(tmp_path) -> None:
    chunks = chunks_from_documents([SOURCE])
    target = write_chunks_json(chunks, tmp_path / "chunks.json")

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert len(loaded) == 2
    assert loaded[0]["chunk_id"] == "xmu_2027_undergraduate_guide#s0"
