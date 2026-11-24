"""Answer-level evaluation for grounded RAG responses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import ceil
from time import perf_counter
from typing import Any

from langchain_core.language_models import BaseChatModel

from study_abroad.grounded import answer_question
from study_abroad.rag import RAGIndex


@dataclass(frozen=True, slots=True)
class AnswerCaseResult:
    case_id: str
    expected_source_ids: tuple[str, ...]
    cited_source_ids: tuple[str, ...]
    citation_hit: bool
    citation_complete: bool
    refusal_expected: bool
    insufficient: bool
    refusal_correct: bool
    latency_ms: float
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AnswerSummary:
    total: int
    citation_hits: int
    citation_complete: int
    refusal_expected: int
    refusal_correct: int
    errors: int
    average_latency_ms: float
    p95_latency_ms: float
    results: tuple[AnswerCaseResult, ...]


def evaluate_answers(
    model: BaseChatModel,
    index: RAGIndex,
    cases: Sequence[Mapping[str, Any]],
    *,
    k: int = 4,
) -> AnswerSummary:
    """Measure citation coverage, refusal behaviour, and generation latency."""
    if not cases:
        raise ValueError("answer evaluation requires at least one case")

    results: list[AnswerCaseResult] = []
    for case in cases:
        case_id = str(case["case_id"])
        expected = tuple(str(source_id) for source_id in case["expected_source_ids"])
        refusal_expected = bool(case.get("expect_insufficient", False))
        started = perf_counter()
        try:
            hits = index.search(str(case["question"]), k=k)
            answer = answer_question(model, str(case["question"]), hits)
        except Exception as error:  # noqa: BLE001 - record per-case failures
            results.append(
                AnswerCaseResult(
                    case_id=case_id,
                    expected_source_ids=expected,
                    cited_source_ids=(),
                    citation_hit=False,
                    citation_complete=False,
                    refusal_expected=refusal_expected,
                    insufficient=False,
                    refusal_correct=False,
                    latency_ms=(perf_counter() - started) * 1000,
                    error=f"{type(error).__name__}: {error}",
                )
            )
            continue

        latency_ms = (perf_counter() - started) * 1000
        cited = tuple(dict.fromkeys(citation.source_id for citation in answer.citations))
        found = set(cited)
        results.append(
            AnswerCaseResult(
                case_id=case_id,
                expected_source_ids=expected,
                cited_source_ids=cited,
                citation_hit=bool(found.intersection(expected)),
                citation_complete=set(expected).issubset(found),
                refusal_expected=refusal_expected,
                insufficient=answer.insufficient_evidence,
                refusal_correct=answer.insufficient_evidence == refusal_expected,
                latency_ms=latency_ms,
            )
        )

    latencies = sorted(result.latency_ms for result in results)
    total = len(results)
    p95_index = max(0, ceil(0.95 * total) - 1)
    return AnswerSummary(
        total=total,
        citation_hits=sum(result.citation_hit for result in results),
        citation_complete=sum(result.citation_complete for result in results),
        refusal_expected=sum(result.refusal_expected for result in results),
        refusal_correct=sum(result.refusal_correct for result in results),
        errors=sum(result.error is not None for result in results),
        average_latency_ms=sum(latencies) / total,
        p95_latency_ms=latencies[p95_index],
        results=tuple(results),
    )
