"""Reproducible Nanjing retrieval evaluation for local embeddings."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from study_abroad.city_catalog import CityPack
from study_abroad.city_rag import chunks_from_catalog_sources, chunks_from_city_pack
from study_abroad.rag import RAGIndex, RetrievalSummary, evaluate_retrieval
from study_abroad.source_snapshots import load_catalog_sources

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings


def load_huggingface_embeddings(model_path: str | Path, device: str) -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=str(Path(model_path)),
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )


def build_nanjing_eval_index(
    *,
    pack_path: str | Path,
    sources_path: str | Path,
    cases_path: str | Path,
    model_path: str | Path,
    persist_directory: str | Path,
    report_path: str | Path,
    project_root: str | Path,
    device: str = "cuda",
) -> RetrievalSummary:
    """Build a Nanjing Chroma index and write a retrieval evaluation report."""
    root = Path(project_root).resolve()
    pack = CityPack(**json.loads(Path(pack_path).read_text(encoding="utf-8")))
    sources = load_catalog_sources(sources_path, root)
    program_chunks = chunks_from_city_pack(pack)
    source_chunks = chunks_from_catalog_sources(pack, sources)
    chunks = [*program_chunks, *source_chunks]
    if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
        raise ValueError("chunk_id values must be unique")

    target = Path(persist_directory)
    if target.exists():
        shutil.rmtree(target)

    embeddings = load_huggingface_embeddings(model_path, device)
    index = RAGIndex(
        embeddings,
        persist_directory=target,
        collection_name="nanjing_bge_m3_full_v1",
    )
    index.add_chunks(chunks)
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))["cases"]
    summary = evaluate_retrieval(index, cases, k=4)

    report = {
        "model": "BAAI/bge-m3",
        "device": device,
        "program_chunks": len(program_chunks),
        "source_chunks": len(source_chunks),
        "total_chunks": len(chunks),
        "summary": asdict(summary),
    }
    report_target = Path(report_path)
    report_target.parent.mkdir(parents=True, exist_ok=True)
    report_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
