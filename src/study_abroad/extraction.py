"""Extract Program records with LangChain structured output and source checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from study_abroad.models import Program
from study_abroad.validation import derive_verification_status

MAX_SOURCE_CHARS = 40_000


class ExtractionError(RuntimeError):
    """Raised when model output is not faithful to the supplied source."""


@dataclass(frozen=True, slots=True)
class ExtractionFailure:
    candidate_id: str
    error: str


@dataclass(frozen=True, slots=True)
class BatchExtractionResult:
    programs: tuple[Program, ...]
    failures: tuple[ExtractionFailure, ...]


_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Extract one university program as the Program schema. "
            "Use null for facts absent from the supplied text; never guess. "
            "Evidence source_quote values must be short verbatim excerpts from the text. "
            "Use only the supplied source_id, source_url, university, and admission_cycle.",
        ),
        (
            "human",
            "Source metadata: {metadata}\n\nOfficial source text:\n{text}",
        ),
    ]
)


def _normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def _build_prompt_text(
    source: Mapping[str, Any],
    text: str,
    related_sources: Sequence[Mapping[str, Any]],
) -> str:
    sections = [f"Source ID: {source['source_id']}\n{text}"]
    sections.extend(
        f"Source ID: {related['source']['source_id']}\n{related['text']}"
        for related in related_sources
    )
    return "\n\n".join(sections)


def _source_documents(
    source: Mapping[str, Any],
    text: str,
    related_sources: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[Mapping[str, Any], str]]:
    documents = {str(source["source_id"]): (source, text)}
    for related in related_sources:
        related_source = related["source"]
        documents[str(related_source["source_id"])] = (
            related_source,
            str(related["text"]),
        )
    return documents


def _check_source_consistency(
    program: Program,
    source: Mapping[str, Any],
    text: str,
    related_sources: Sequence[Mapping[str, Any]],
) -> None:
    expected = {
        "university": source["university"],
        "admission_cycle": source["admission_cycle"],
    }
    for field, expected_value in expected.items():
        if getattr(program, field) != expected_value:
            raise ExtractionError(f"{field} does not match the supplied source")

    documents = _source_documents(source, text, related_sources)
    for item in program.evidence:
        if item.source_id not in documents:
            raise ExtractionError("evidence points to a different source")
        evidence_source, evidence_text = documents[item.source_id]
        if str(item.source_url) != evidence_source["url"]:
            raise ExtractionError("evidence points to a different source")
        if _normalized(item.source_quote) not in _normalized(evidence_text):
            raise ExtractionError(f"evidence quote is not present in source: {item.field_name}")


def extract_program(
    model: BaseChatModel,
    source: Mapping[str, Any],
    text: str,
    *,
    collected_at: datetime,
    related_sources: Sequence[Mapping[str, Any]] = (),
) -> Program:
    """Extract one record, reject unsupported evidence, then derive its status."""
    if not text.strip():
        raise ValueError("source text must not be empty")
    prompt_text = _build_prompt_text(source, text, related_sources)
    if len(prompt_text) > MAX_SOURCE_CHARS:
        raise ValueError("source text is too large; provide focused sections")

    metadata = {
        "primary_source": {
            "source_id": source["source_id"],
            "university": source["university"],
            "source_url": source["url"],
            "admission_cycle": source["admission_cycle"],
        },
        "related_sources": [
            {
                "source_id": related["source"]["source_id"],
                "source_url": related["source"]["url"],
                "university": related["source"]["university"],
                "admission_cycle": related["source"]["admission_cycle"],
            }
            for related in related_sources
        ],
    }
    structured_model = model.with_structured_output(Program)
    candidate = (_PROMPT | structured_model).invoke({"metadata": metadata, "text": prompt_text})
    if not isinstance(candidate, Program):
        raise ExtractionError("model did not return a Program instance")

    _check_source_consistency(candidate, source, text, related_sources)
    candidate = candidate.model_copy(update={"collected_at": collected_at})
    status = derive_verification_status(candidate)
    return candidate.model_copy(update={"verification_status": status})


def extract_programs(
    model: BaseChatModel,
    candidates: Sequence[Mapping[str, Any]],
    sources: Sequence[Mapping[str, Any]],
    source_documents: Mapping[str, str],
    *,
    collected_at: datetime,
) -> BatchExtractionResult:
    """Extract candidates independently and preserve valid results when one fails."""
    source_by_id = {str(source["source_id"]): source for source in sources}
    programs: list[Program] = []
    failures: list[ExtractionFailure] = []

    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        try:
            source = source_by_id[str(candidate["source_id"])]
            related_sources = [
                {"source": related, "text": source_documents[related_id]}
                for related_id, related in source_by_id.items()
                if related_id != candidate["source_id"]
                and related["university"] == source["university"]
                and related_id in source_documents
            ]
            program = extract_program(
                model,
                source,
                str(candidate["text"]),
                collected_at=collected_at,
                related_sources=related_sources,
            )
            programs.append(program.model_copy(update={"program_id": candidate_id}))
        except (ExtractionError, ValueError, KeyError) as exc:
            failures.append(ExtractionFailure(candidate_id=candidate_id, error=str(exc)))

    return BatchExtractionResult(programs=tuple(programs), failures=tuple(failures))
