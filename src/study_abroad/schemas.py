"""Schemas for the pre-sales recommendation workflow."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EducationStatus(StrEnum):
    GRADUATED = "graduated"
    EXPECTED_GRADUATION = "expected_graduation"
    IN_PROGRESS = "in_progress"


class ChineseLevel(StrEnum):
    NONE = "none"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class CampusType(StrEnum):
    URBAN = "urban"
    SUBURBAN = "suburban"
    NO_PREFERENCE = "no_preference"


class RecommendationPriority(StrEnum):
    CITY = "city"
    SCHOOL_TIER = "school_tier"
    COST = "cost"
    LANGUAGE = "language"


class Education(ContractBase):
    current_education_level: str = Field(min_length=1)
    graduation_status: EducationStatus
    school_name: str | None
    gpa_or_ranking: str | None


class Language(ContractBase):
    native_language: str = Field(min_length=1)
    chinese_level: ChineseLevel | None
    hsk_level: int | None = Field(ge=1, le=6)
    hsk_score: int | None = Field(ge=0, le=300)
    ielts_score: float | None = Field(ge=0, le=9)
    toefl_score: int | None = Field(ge=0, le=120)
    other_language_cert: str | None


class Constraints(ContractBase):
    annual_budget_cny: float | None = Field(ge=0)
    preferred_school_tiers: list[str] = Field(default_factory=list)
    preferred_campus_type: CampusType | None
    needs_dormitory: bool | None


class Preferences(ContractBase):
    preferred_universities: list[str] = Field(default_factory=list)
    excluded_universities: list[str] = Field(default_factory=list)
    priority_ranking: list[RecommendationPriority] = Field(default_factory=list)
    special_notes: str | None


class StudentIntake(ContractBase):
    intake_id: str = Field(min_length=1)
    student_ref: str | None
    preferred_city: str = Field(min_length=1)
    backup_cities: list[str] = Field(default_factory=list)
    target_program_type: str = Field(min_length=1)
    target_intake_cycle: str = Field(min_length=1)
    created_at: datetime
    education: Education
    language: Language
    constraints: Constraints
    preferences: Preferences


class EvidenceRef(ContractBase):
    source_id: str = Field(min_length=1)
    source_url: HttpUrl
    source_title: str = Field(min_length=1)
    source_quote: str = Field(min_length=1)
    admission_cycle: str = Field(min_length=1)
    accessed_at: date


class TierItem(ContractBase):
    university: str = Field(min_length=1)
    city: str = Field(min_length=1)
    program_name: str = Field(min_length=1)
    program_type: str = Field(min_length=1)
    instruction_language: str = Field(min_length=1)
    duration_text: str = Field(min_length=1)
    tuition_amount: float | None = Field(ge=0)
    tuition_currency: str | None
    tuition_period: str | None
    application_deadline: date | None
    requirement_summary: list[str] = Field(default_factory=list)
    fit_summary: str = Field(min_length=1)
    flags: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class Tier(ContractBase):
    tier_name: str = Field(min_length=1)
    tier_label: str = Field(min_length=1)
    items: list[TierItem] = Field(default_factory=list)


class RecommendationReport(ContractBase):
    report_id: str = Field(min_length=1)
    intake_id: str = Field(min_length=1)
    city: str = Field(min_length=1)
    target_program_type: str = Field(min_length=1)
    generated_at: datetime
    summary: str = Field(min_length=1)
    tiers: list[Tier] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    disclaimer: str = Field(min_length=1)
