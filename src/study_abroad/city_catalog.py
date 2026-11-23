"""City-level catalog schemas for the pre-sales recommendation workflow."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CatalogBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    CONFLICTING = "conflicting"
    STALE = "stale"
    UNVERIFIED = "unverified"


class PoolStatus(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    EXCLUDED_NO_OFFICIAL_DATA = "excluded_no_official_data"
    EXCLUDED_OUT_OF_SCOPE = "excluded_out_of_scope"


class CatalogEvidenceRef(CatalogBase):
    source_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_quote: str = Field(min_length=1)
    admission_cycle: str = Field(min_length=1)
    accessed_at: date


class ProgramRequirements(CatalogBase):
    education_level_required: str | None
    chinese_level_required: str | None
    hsk_level_required: int | None = Field(ge=1, le=6)
    hsk_score_required: int | None = Field(ge=0, le=300)
    ielts_score_required: float | None = Field(ge=0, le=9)
    toefl_score_required: int | None = Field(ge=0, le=120)
    other_requirements: list[str] = Field(default_factory=list)


class ProgramEntry(CatalogBase):
    program_id: str = Field(min_length=1)
    university: str = Field(min_length=1)
    city: str = Field(min_length=1)
    program_name: str = Field(min_length=1)
    program_type: str = Field(min_length=1)
    admission_cycle: str = Field(min_length=1)
    instruction_language: str = Field(min_length=1)
    duration_text: str = Field(min_length=1)
    tuition_amount: float | None = Field(ge=0)
    tuition_currency: str | None
    tuition_period: str | None
    application_deadline: date | None
    requirements: ProgramRequirements
    evidence: list[CatalogEvidenceRef] = Field(default_factory=list)
    verification_status: VerificationStatus
    review_flags: list[str] = Field(default_factory=list)
    last_reviewed_at: datetime | None


class UniversityEntry(CatalogBase):
    university: str = Field(min_length=1)
    city: str = Field(min_length=1)
    tier_hint: str = Field(min_length=1)
    pool_status: PoolStatus
    review_flags: list[str] = Field(default_factory=list)
    official_programs: list[ProgramEntry] = Field(default_factory=list)


class CityPack(CatalogBase):
    city_pack_id: str = Field(min_length=1)
    city: str = Field(min_length=1)
    country: str = Field(min_length=1)
    target_program_type: str = Field(min_length=1)
    admission_cycle: str = Field(min_length=1)
    version: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    universities: list[UniversityEntry] = Field(default_factory=list)
