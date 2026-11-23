from __future__ import annotations

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from study_abroad.chunking import Chunk
from study_abroad.rag import RAGIndex, evaluate_retrieval


def _chunk(
    chunk_id: str = "xmu_fees#s1",
    text: str = "Tuition is RMB 26,000/year.",
    university: str = "Xiamen University",
    admission_cycle: str = "2027_entry",
    source_type: str = "web_section",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=f"{chunk_id.split('#')[0]}",
        program_id=None,
        university=university,
        admission_cycle=admission_cycle,
        source_url="https://example.edu/guide",
        source_quote=text,
        collected_at="2026-11-22T00:00:00Z",
        text=text,
        source_type=source_type,
    )


def _index(tmp_path) -> RAGIndex:
    return RAGIndex(
        DeterministicFakeEmbedding(size=64),
        persist_directory=tmp_path / "chroma",
        collection_name="test_collection",
    )


def test_add_and_search_returns_hit_with_source_metadata(tmp_path) -> None:
    index = _index(tmp_path)
    chunk = _chunk()
    index.add_chunks([chunk])

    hits = index.search(chunk.text, k=1)

    assert len(hits) == 1
    assert hits[0].chunk_id == chunk.chunk_id
    assert hits[0].university == "Xiamen University"
    assert hits[0].admission_cycle == "2027_entry"
    assert hits[0].source_url == chunk.source_url
    assert hits[0].source_quote == chunk.source_quote
    assert isinstance(hits[0].distance, float)


def test_search_filters_by_university_and_cycle(tmp_path) -> None:
    index = _index(tmp_path)
    xmu = _chunk("xmu_fees#s1", "Tuition is RMB 26,000/year.")
    fdu = _chunk(
        "fdu_tuition#p1",
        "Clinical Medicine tuition is RMB 42,000/year.",
        university="Fudan University",
    )
    old = _chunk("xmu_old#s1", "Old tuition is RMB 20,000/year.", admission_cycle="2026_entry")
    index.add_chunks([xmu, fdu, old])

    hits = index.search(
        "Tuition",
        k=10,
        university="Xiamen University",
        admission_cycle="2027_entry",
    )

    assert hits
    assert all(hit.university == "Xiamen University" for hit in hits)
    assert all(hit.admission_cycle == "2027_entry" for hit in hits)
    assert all(hit.chunk_id != "fdu_tuition#p1" for hit in hits)


def test_program_metadata_is_preserved(tmp_path) -> None:
    index = _index(tmp_path)
    chunk = Chunk(
        chunk_id="xmu_cs#fact",
        document_id="xmu_catalog",
        program_id="xmu_cs",
        university="Xiamen University",
        admission_cycle="2027_entry",
        source_url="https://example.edu/catalog",
        source_quote="Computer Science and Technology",
        collected_at="2026-11-22T00:00:00Z",
        text="Computer Science and Technology at Xiamen University.",
        source_type="program_fact",
    )
    index.add_chunks([chunk])

    hit = index.search(chunk.text, k=1)[0]

    assert hit.program_id == "xmu_cs"
    assert hit.source_type == "program_fact"


def test_empty_query_and_invalid_k_are_rejected(tmp_path) -> None:
    index = _index(tmp_path)

    with pytest.raises(ValueError, match="must not be empty"):
        index.search("  ")
    with pytest.raises(ValueError, match="at least 1"):
        index.search("tuition", k=0)


def test_duplicate_chunk_ids_are_rejected_before_write(tmp_path) -> None:
    index = _index(tmp_path)
    chunk = _chunk()
    with pytest.raises(ValueError, match="unique"):
        index.add_chunks([chunk, chunk])


def test_retrieval_evaluation_reports_hit_and_complete_separately(tmp_path) -> None:
    index = _index(tmp_path)
    xmu = _chunk("xmu_fees#s1", "Xiamen University tuition is RMB 26,000/year.")
    fdu = _chunk(
        "fdu_tuition#p1",
        "Fudan University clinical medicine tuition is RMB 42,000/year.",
        university="Fudan University",
    )
    index.add_chunks([xmu, fdu])
    cases = [
        {
            "case_id": "hit_one",
            "question": xmu.text,
            "expected_source_ids": [xmu.document_id, fdu.document_id],
        },
        {
            "case_id": "miss",
            "question": fdu.text,
            "expected_source_ids": ["missing_source"],
        },
    ]

    summary = evaluate_retrieval(index, cases, k=1)

    assert summary.total == 2
    assert summary.hits == 1
    assert summary.complete == 0
    assert summary.hit_rate == 0.5
    assert summary.complete_rate == 0.0
    assert summary.average_latency_ms >= 0
    assert summary.p50_latency_ms >= 0
    assert summary.p95_latency_ms >= summary.p50_latency_ms
    assert [result.hit for result in summary.results] == [True, False]
