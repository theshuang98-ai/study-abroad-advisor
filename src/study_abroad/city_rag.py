"""Convert city catalog records into retrieval chunks."""

from __future__ import annotations

from collections.abc import Mapping

from study_abroad.catalog_validation import CatalogSource
from study_abroad.chunking import Chunk
from study_abroad.city_catalog import CityPack, ProgramEntry

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150


def _program_text(program: ProgramEntry) -> str:
    requirements = program.requirements
    tuition_amount = (
        f"{program.tuition_amount:g}"
        if program.tuition_amount is not None
        else "unknown"
    )
    return "\n".join(
        [
            f"University: {program.university}",
            f"City: {program.city}",
            f"Program: {program.program_name}",
            f"Type: {program.program_type}",
            f"Admission cycle: {program.admission_cycle}",
            f"Instruction language: {program.instruction_language}",
            f"Duration: {program.duration_text}",
            f"Tuition: {tuition_amount} {program.tuition_currency or ''} "
            f"per {program.tuition_period or 'unknown'}",
            f"Application deadline: {program.application_deadline or 'unknown'}",
            f"Education requirement: {requirements.education_level_required or 'unknown'}",
            f"Chinese requirement: {requirements.chinese_level_required or 'unknown'}",
            f"Other requirements: {'; '.join(requirements.other_requirements)}",
            f"Verification status: {program.verification_status.value}",
            f"Review flags: {'; '.join(program.review_flags)}",
        ]
    )


def chunks_from_city_pack(pack: CityPack) -> list[Chunk]:
    """Create one fact chunk per program in a CityPack."""
    chunks: list[Chunk] = []
    for university in pack.universities:
        for program in university.official_programs:
            if not program.evidence:
                continue
            source = program.evidence[0]
            chunks.append(
                Chunk(
                    chunk_id=f"{program.program_id}#city_fact",
                    document_id=source.source_id,
                    program_id=program.program_id,
                    university=program.university,
                    admission_cycle=program.admission_cycle,
                    source_url=str(source.source_url),
                    source_quote=source.source_quote,
                    collected_at=(
                        program.last_reviewed_at or pack.updated_at
                    ).isoformat(),
                    text=_program_text(program),
                    source_type="program_fact",
                )
            )
    return chunks


def _split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split visible source text near sentence boundaries with bounded overlap."""
    if len(text) <= chunk_size:
        return [text]
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window = text[start:end]
            for separator in ("。", "；", ". ", " "):
                position = window.rfind(separator)
                if position >= chunk_size // 2:
                    end = start + position + len(separator)
                    break
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return pieces


def chunks_from_catalog_sources(
    pack: CityPack,
    sources: Mapping[str, CatalogSource],
) -> list[Chunk]:
    """Create retrieval chunks from official page snapshots."""
    chunks: list[Chunk] = []
    for source in sources.values():
        for index, piece in enumerate(_split_text(source.text)):
            chunks.append(
                Chunk(
                    chunk_id=f"{source.source_id}:bgc{index:03d}",
                    document_id=source.source_id,
                    program_id=None,
                    university=source.university,
                    admission_cycle=pack.admission_cycle,
                    source_url=source.url,
                    source_quote=piece[:300],
                    collected_at=source.accessed_at or pack.updated_at.isoformat(),
                    text=f"{source.title}\n{piece}" if source.title else piece,
                    source_type="web_snapshot",
                )
            )
    return chunks
