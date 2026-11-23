"""Build stable, source-grounded chunks from ingested and extracted records."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from study_abroad.models import Program


class ChunkingError(RuntimeError):
    """Raised when a source does not match the expected ingested shape."""


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_id: str
    document_id: str
    program_id: str | None
    university: str
    admission_cycle: str
    source_url: str
    source_quote: str
    collected_at: str
    text: str
    source_type: str


def _normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def _quote_source(document: Mapping[str, Any], text: str) -> str:
    title = str(document.get("title") or "").strip()
    if title:
        return title
    normalized_text = _normalized(text)
    if normalized_text:
        for line in text.splitlines():
            line = line.strip()
            if line:
                return line
    raise ChunkingError(f"missing source quote for document {document['document_id']}")


def _quote_program(program: Program) -> str:
    for item in program.evidence:
        if item.field_name == "program_name_original":
            return item.source_quote
    return program.program_name_original


def _quote_evidence(document: Mapping[str, Any], program: Program) -> str:
    if program.evidence:
        quote = program.evidence[0].source_quote
        text = _normalized(str(document.get("text") or ""))
        if _normalized(quote) in text:
            return quote
    return _quote_program(program)


def _validate_program_record(program: Program) -> None:
    if program.verification_status.value == "verified" and not program.evidence:
        raise ChunkingError(f"verified program is missing evidence: {program.program_id}")


def chunks_from_programs(
    programs: Sequence[Mapping[str, Any]],
    sources: Mapping[str, Mapping[str, Any]],
) -> list[Chunk]:
    """Create one retrieval chunk per program record."""
    chunks: list[Chunk] = []
    for raw in programs:
        program = Program(**raw)
        source_by_id = {source_id: record for source_id, record in sources.items()}
        primary_source = None
        if program.evidence:
            for item in program.evidence:
                if item.source_id in source_by_id:
                    primary_source = source_by_id[item.source_id]
                    break
        if primary_source is None:
            raise ChunkingError(f"missing source for program {program.program_id}")
        _validate_program_record(program)
        quote = _quote_evidence(primary_source, program)
        chunks.append(
            Chunk(
                chunk_id=f"{program.program_id}#fact",
                document_id=str(primary_source["document_id"]),
                program_id=program.program_id,
                university=program.university,
                admission_cycle=program.admission_cycle,
                source_url=str(primary_source["url"]),
                source_quote=quote,
                collected_at=str(program.collected_at.isoformat()),
                text=(
                    f"{program.program_name_original} at {program.university}. "
                    f"Degree level: "
                    f"{program.degree_level.value if program.degree_level else None}. "
                    f"Instruction languages: {program.instruction_languages}. "
                    f"Duration: {program.duration_text}. "
                    f"Tuition: {program.tuition_amount} {program.tuition_currency or ''} "
                    f"per {program.tuition_period.value if program.tuition_period else 'unknown'}. "
                    f"Deadline: {program.application_deadline or program.deadline_text}. "
                    f"Requirements: "
                    f"{program.language_requirements or program.academic_requirements or []}. "
                    f"Evidence: {program.evidence[0].source_quote if program.evidence else ''}"
                ),
                source_type="program_fact",
            )
        )
    return chunks


def chunks_from_documents(documents: Sequence[Mapping[str, Any]]) -> list[Chunk]:
    """Create chunks for PDF pages or webpage sections."""
    chunks: list[Chunk] = []
    for document in documents:
        source_type = document.get("source_type")
        if source_type == "official_pdf":
            pages = document.get("pages")
            if not isinstance(pages, list) or not pages:
                raise ChunkingError(f"PDF document has no pages: {document['document_id']}")
            for page in pages:
                text = str(page.get("text") or "").strip()
                if not text:
                    continue
                chunks.append(
                    Chunk(
                        chunk_id=f"{document['document_id']}:p{int(page['page_number']):02d}",
                        document_id=str(document["document_id"]),
                        program_id=None,
                        university=str(document["university"]),
                        admission_cycle=str(document["admission_cycle"]),
                        source_url=str(document["url"]),
                        source_quote=_quote_source(document, text),
                        collected_at=str(document["accessed_at"]),
                        text=text,
                        source_type="pdf_page",
                    )
                )
            continue
        if source_type == "official_webpage":
            sections = document.get("sections")
            if not isinstance(sections, list) or not sections:
                raise ChunkingError(f"web document has no sections: {document['document_id']}")
            for _index, section in enumerate(sections):
                text = str(section.get("text") or "").strip()
                heading = str(section.get("heading") or "").strip()
                if not text and not heading:
                    continue
                chunk_text = "\n".join(part for part in (heading, text) if part)
                quote = text.splitlines()[0].strip() if text else heading
                chunks.append(
                    Chunk(
                        chunk_id=str(section["section_id"]),
                        document_id=str(document["document_id"]),
                        program_id=None,
                        university=str(document["university"]),
                        admission_cycle=str(document["admission_cycle"]),
                        source_url=str(document["url"]),
                        source_quote=quote,
                        collected_at=str(document["accessed_at"]),
                        text=chunk_text,
                        source_type="web_section",
                    )
                )
            continue
        raise ChunkingError(f"unsupported source_type for chunking: {source_type}")
    return chunks


def write_chunks_json(chunks: Sequence[Chunk], out_path: str | Path) -> Path:
    """Write chunks as JSON for manual review and later indexing."""
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps([asdict(chunk) for chunk in chunks], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target
