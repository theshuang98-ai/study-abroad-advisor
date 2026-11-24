"""Local vector index over source-grounded chunks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from study_abroad.chunking import Chunk


@dataclass(frozen=True, slots=True)
class SearchHit:
    chunk_id: str
    text: str
    distance: float
    document_id: str
    program_id: str | None
    university: str
    admission_cycle: str
    source_url: str
    source_quote: str
    source_type: str
    collected_at: str = ""


@dataclass(frozen=True, slots=True)
class RetrievalCaseResult:
    case_id: str
    question: str
    expected_source_ids: tuple[str, ...]
    retrieved_source_ids: tuple[str, ...]
    hit: bool
    complete: bool
    latency_ms: float


@dataclass(frozen=True, slots=True)
class RetrievalSummary:
    k: int
    total: int
    hits: int
    complete: int
    hit_rate: float
    complete_rate: float
    average_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    results: tuple[RetrievalCaseResult, ...]


def _metadata(chunk: Chunk) -> dict[str, str]:
    metadata = {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "university": chunk.university,
        "admission_cycle": chunk.admission_cycle,
        "source_url": chunk.source_url,
        "source_quote": chunk.source_quote,
        "collected_at": chunk.collected_at,
        "source_type": chunk.source_type,
    }
    if chunk.program_id is not None:
        metadata["program_id"] = chunk.program_id
    return metadata


def _where(
    university: str | None,
    admission_cycle: str | None,
) -> dict[str, Any] | None:
    conditions = []
    if university is not None:
        conditions.append({"university": university})
    if admission_cycle is not None:
        conditions.append({"admission_cycle": admission_cycle})
    if not conditions:
        return None
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


class RAGIndex:
    """Thin Chroma wrapper that keeps source metadata on every result."""

    def __init__(
        self,
        embeddings: Embeddings,
        persist_directory: str | Path | None = None,
        collection_name: str = "study_abroad",
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        self._store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=str(persist_directory) if persist_directory else None,
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk_id values must be unique")
        self._store.add_texts(
            texts=[chunk.text for chunk in chunks],
            metadatas=[_metadata(chunk) for chunk in chunks],
            ids=chunk_ids,
        )

    def search(
        self,
        query: str,
        *,
        k: int = 4,
        university: str | None = None,
        admission_cycle: str | None = None,
    ) -> list[SearchHit]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if k < 1:
            raise ValueError("k must be at least 1")
        results = self._store.similarity_search_with_score(
            query,
            k=k,
            filter=_where(university, admission_cycle),
        )
        return [
            _hit(document.metadata, document.page_content, float(distance))
            for document, distance in results
        ]


def evaluate_retrieval(
    index: RAGIndex,
    cases: Sequence[Mapping[str, Any]],
    *,
    k: int = 4,
) -> RetrievalSummary:
    """Evaluate source recall only; this does not measure answer quality."""
    if not cases:
        raise ValueError("retrieval evaluation requires at least one case")

    results: list[RetrievalCaseResult] = []
    for case in cases:
        expected = tuple(str(source_id) for source_id in case["expected_source_ids"])
        if not expected:
            continue
        started = perf_counter()
        hits = index.search(
            str(case["question"]),
            k=k,
            university=case.get("university"),
        )
        latency_ms = (perf_counter() - started) * 1000
        retrieved = tuple(dict.fromkeys(hit.document_id for hit in hits))
        found = set(retrieved)
        results.append(
            RetrievalCaseResult(
                case_id=str(case["case_id"]),
                question=str(case["question"]),
                expected_source_ids=expected,
                retrieved_source_ids=retrieved,
                hit=bool(found.intersection(expected)),
                complete=set(expected).issubset(found),
                latency_ms=latency_ms,
            )
        )

    if not results:
        raise ValueError("retrieval cases have no expected_source_ids")
    hits = sum(result.hit for result in results)
    complete = sum(result.complete for result in results)
    total = len(results)
    latencies = sorted(result.latency_ms for result in results)
    p95_index = max(0, ceil(0.95 * total) - 1)
    return RetrievalSummary(
        k=k,
        total=total,
        hits=hits,
        complete=complete,
        hit_rate=hits / total,
        complete_rate=complete / total,
        average_latency_ms=sum(latencies) / total,
        p50_latency_ms=median(latencies),
        p95_latency_ms=latencies[p95_index],
        results=tuple(results),
    )


def _hit(metadata: Mapping[str, Any], text: str, distance: float) -> SearchHit:
    return SearchHit(
        chunk_id=str(metadata.get("chunk_id", "")),
        text=text,
        distance=distance,
        document_id=str(metadata["document_id"]),
        program_id=str(metadata["program_id"]) if metadata.get("program_id") else None,
        university=str(metadata["university"]),
        admission_cycle=str(metadata["admission_cycle"]),
        source_url=str(metadata["source_url"]),
        source_quote=str(metadata["source_quote"]),
        source_type=str(metadata["source_type"]),
        collected_at=str(metadata.get("collected_at", "")),
    )
