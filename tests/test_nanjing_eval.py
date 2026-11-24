from __future__ import annotations

import pytest
from langchain_core.embeddings import Embeddings

from study_abroad.chunking import Chunk
from study_abroad.nanjing_eval import build_nanjing_eval_index, build_nanjing_retriever
from study_abroad.rag import RAGIndex


class _FakeEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 0.0] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 0.0]


def test_build_nanjing_eval_index_is_reproducible(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "study_abroad.nanjing_eval.load_huggingface_embeddings",
        lambda model_path, device: _FakeEmbeddings(),
    )
    summary = build_nanjing_eval_index(
        pack_path="data/city_packs/nanjing_pack_v1.json",
        sources_path="data/city_packs/nanjing_sources.json",
        cases_path="evals/nanjing_cases.json",
        model_path=".local/models/bge-m3",
        persist_directory=tmp_path / "chroma",
        report_path=tmp_path / "report.json",
        project_root=".",
        device="cpu",
    )

    report = (tmp_path / "report.json").read_text(encoding="utf-8")
    assert "program_chunks" in report
    assert "source_chunks" in report
    assert "summary" in report
    assert summary.total == 18
    assert summary.average_latency_ms >= 0


def test_build_nanjing_retriever_returns_source_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "study_abroad.nanjing_eval.load_huggingface_embeddings",
        lambda model_path, device: _FakeEmbeddings(),
    )
    persist = tmp_path / "chroma"
    chunk = Chunk(
        chunk_id="nju_page#s1",
        document_id="nju_page",
        program_id=None,
        university="Nanjing University",
        admission_cycle="2027_fall",
        source_url="https://example.edu/guide",
        source_quote="Tuition is 21000 CNY per year.",
        collected_at="2026-11-23",
        text="Tuition is 21000 CNY per year.",
        source_type="web_snapshot",
    )
    RAGIndex(
        _FakeEmbeddings(),
        persist_directory=persist,
        collection_name="test_nanjing",
    ).add_chunks([chunk])

    retriever = build_nanjing_retriever(
        model_path="ignored",
        persist_directory=persist,
        collection_name="test_nanjing",
        device="cpu",
        k=1,
    )
    hits = retriever("tuition")

    assert hits[0]["chunk_id"] == "nju_page#s1"
    assert hits[0]["document_id"] == "nju_page"
    assert hits[0]["source_url"] == "https://example.edu/guide"
    assert hits[0]["collected_at"] == "2026-11-23"


def test_retriever_requires_existing_index(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        build_nanjing_retriever(
            model_path="ignored",
            persist_directory=tmp_path / "missing",
            device="cpu",
        )
