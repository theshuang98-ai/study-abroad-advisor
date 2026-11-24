"""Generate answers grounded in retrieved chunks with validated citations."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field

from study_abroad.rag import SearchHit

MAX_EVIDENCE_CHARS = 1500


class GroundedAnswerError(RuntimeError):
    """Raised when the model cites evidence that was not retrieved."""


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    admission_cycle: str = Field(min_length=1)
    accessed_at: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    answer: str = Field(min_length=1)
    citations: list[Citation] = Field(default_factory=list)
    insufficient_evidence: bool = False


_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer using only the numbered official evidence. Never use outside knowledge. "
            "If the evidence does not contain the answer, set insufficient_evidence=true and "
            "state that official sources do not confirm it. For every factual claim, add a "
            "citation with the exact source_id, source_url, admission_cycle, accessed_at, and a "
            "short verbatim quote copied from that evidence. Never invent fees or deadlines.",
        ),
        ("human", "Question:\n{question}\n\nOfficial evidence:\n{evidence}"),
    ]
)


def _normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def _evidence_block(hits: Sequence[SearchHit]) -> str:
    blocks = []
    for index, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{index}] source_id={hit.document_id} | university={hit.university} | "
            f"cycle={hit.admission_cycle} | accessed_at={hit.collected_at} | "
            f"url={hit.source_url}\n{hit.text[:MAX_EVIDENCE_CHARS]}"
        )
    return "\n\n".join(blocks)


def _validate_citations(
    answer: GroundedAnswer,
    hits: Sequence[SearchHit],
) -> GroundedAnswer:
    if answer.insufficient_evidence:
        return answer
    if not answer.citations:
        raise GroundedAnswerError("answer has no citations")

    validated: list[Citation] = []
    for citation in answer.citations:
        supported = any(
            hit.document_id == citation.source_id
            and hit.source_url == citation.source_url
            and hit.admission_cycle == citation.admission_cycle
            and _normalized(citation.quote) in _normalized(hit.text)
            for hit in hits
        )
        if not supported:
            raise GroundedAnswerError(
                f"citation is not supported by retrieved evidence: {citation.source_id}"
            )
        validated.append(citation)
    return answer.model_copy(update={"citations": validated})


def answer_question(
    model: BaseChatModel,
    question: str,
    hits: Sequence[SearchHit],
) -> GroundedAnswer:
    """Answer a question or refuse when no official evidence was retrieved."""
    if not question.strip():
        raise ValueError("question must not be empty")
    if not hits:
        return GroundedAnswer(
            answer="未检索到可核验的官网证据，无法回答该问题。",
            citations=[],
            insufficient_evidence=True,
        )

    structured_model = model.with_structured_output(GroundedAnswer, method="function_calling")
    result = (_PROMPT | structured_model).invoke(
        {"question": question, "evidence": _evidence_block(hits)}
    )
    if not isinstance(result, GroundedAnswer):
        raise GroundedAnswerError("model did not return a GroundedAnswer instance")
    return _validate_citations(result, hits)
