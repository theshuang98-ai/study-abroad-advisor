from __future__ import annotations

from langchain_core.embeddings import Embeddings

from study_abroad.nanjing_eval import build_nanjing_eval_index


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
