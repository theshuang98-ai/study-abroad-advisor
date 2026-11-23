"""Deterministic evidence checks for city catalog entries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from study_abroad.city_catalog import CityPack, PoolStatus


@dataclass(frozen=True, slots=True)
class CatalogSource:
    source_id: str
    url: str
    text: str
    university: str = ""
    title: str = ""
    accessed_at: str = ""


@dataclass(frozen=True, slots=True)
class CatalogValidationIssue:
    code: str
    program_id: str
    source_id: str | None
    message: str


def _normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def validate_catalog_evidence(
    pack: CityPack,
    sources: Mapping[str, CatalogSource],
) -> list[CatalogValidationIssue]:
    """Check that each catalog citation exists and matches its source text."""
    issues: list[CatalogValidationIssue] = []
    for university in pack.universities:
        for program in university.official_programs:
            if not program.evidence:
                if university.pool_status == PoolStatus.ACTIVE:
                    issues.append(
                        CatalogValidationIssue(
                            code="evidence_missing",
                            program_id=program.program_id,
                            source_id=None,
                            message="active program requires evidence",
                        )
                    )
                continue

            for evidence in program.evidence:
                source = sources.get(evidence.source_id)
                if source is None:
                    issues.append(
                        CatalogValidationIssue(
                            code="source_not_found",
                            program_id=program.program_id,
                            source_id=evidence.source_id,
                            message="evidence source is not available locally",
                        )
                    )
                    continue
                if str(evidence.source_url) != source.url:
                    issues.append(
                        CatalogValidationIssue(
                            code="source_url_mismatch",
                            program_id=program.program_id,
                            source_id=evidence.source_id,
                            message="evidence URL differs from source record",
                        )
                    )
                if _normalized(evidence.source_quote) not in _normalized(source.text):
                    issues.append(
                        CatalogValidationIssue(
                            code="quote_not_found",
                            program_id=program.program_id,
                            source_id=evidence.source_id,
                            message="evidence quote is absent from source text",
                        )
                    )
    return issues
