"""Typed data contracts for source-grounded program records."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer


class DegreeLevel(StrEnum):
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTOR = "doctor"
    NON_DEGREE = "non_degree"
    UNKNOWN = "unknown"


class TuitionPeriod(StrEnum):
    YEAR = "year"
    SEMESTER = "semester"
    PROGRAM = "program"
    UNKNOWN = "unknown"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    CONFLICTING = "conflicting"
    STALE = "stale"
    UNVERIFIED = "unverified"


class ContractModel(BaseModel):
    """Reject unexpected model fields instead of silently accepting them."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Evidence(ContractModel):
    source_id: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    source_url: HttpUrl
    source_quote: str = Field(min_length=1)
    admission_cycle: str = Field(min_length=1)
    collected_at: datetime


class Program(ContractModel):
    """Program fields are required keys, but nullable values mean unknown."""

    program_id: str = Field(min_length=1)
    university: str = Field(min_length=1)
    program_name_original: str = Field(min_length=1)
    degree_level: DegreeLevel | None
    is_degree_program: bool | None
    academic_field: str | None
    instruction_languages: list[str] | None
    duration_text: str | None
    tuition_amount: Decimal | None = Field(ge=0)
    tuition_currency: str | None
    tuition_period: TuitionPeriod | None
    tuition_text: str | None
    application_deadline: date | None
    deadline_text: str | None
    language_requirements: list[str] | None
    academic_requirements: list[str] | None
    admission_cycle: str = Field(min_length=1)
    verification_status: VerificationStatus
    evidence: list[Evidence]
    collected_at: datetime

    @field_serializer("tuition_amount", when_used="json")
    def serialize_tuition_amount(self, value: Decimal | None) -> int | float | None:
        """Keep JSON amounts numeric while retaining Decimal in Python."""
        if value is None:
            return None
        return int(value) if value == value.to_integral_value() else float(value)
