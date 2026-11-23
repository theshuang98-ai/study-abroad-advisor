"""Deterministic consistency and evidence checks for Program records."""

from __future__ import annotations

from dataclasses import dataclass

from study_abroad.models import DegreeLevel, Program, TuitionPeriod, VerificationStatus

_DEGREE_LEVELS = {DegreeLevel.BACHELOR, DegreeLevel.MASTER, DegreeLevel.DOCTOR}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    field_name: str
    message: str


def _has_evidence(program: Program, *field_names: str) -> bool:
    accepted = set(field_names)
    return any(item.field_name in accepted for item in program.evidence)


def validate_program(program: Program) -> list[ValidationIssue]:
    """Return every detectable inconsistency; do not infer missing facts."""
    issues: list[ValidationIssue] = []

    if program.is_degree_program is None or program.degree_level in {
        None,
        DegreeLevel.UNKNOWN,
    }:
        issues.append(
            ValidationIssue("degree_unknown", "degree_level", "degree status is unknown")
        )
    elif program.is_degree_program:
        if program.degree_level not in _DEGREE_LEVELS:
            issues.append(
                ValidationIssue(
                    "degree_level_mismatch",
                    "degree_level",
                    "degree program must have bachelor, master, or doctor level",
                )
            )
        if not _has_evidence(program, "is_degree_program", "degree_level"):
            issues.append(
                ValidationIssue(
                    "degree_evidence_missing",
                    "degree_level",
                    "degree claim requires evidence",
                )
            )
    elif program.degree_level in _DEGREE_LEVELS:
        issues.append(
            ValidationIssue(
                "degree_flag_mismatch",
                "is_degree_program",
                "non-degree flag conflicts with degree level",
            )
        )

    if program.tuition_amount is not None:
        if not program.tuition_currency:
            issues.append(
                ValidationIssue(
                    "tuition_currency_missing",
                    "tuition_currency",
                    "tuition amount requires currency",
                )
            )
        if program.tuition_period in {None, TuitionPeriod.UNKNOWN}:
            issues.append(
                ValidationIssue(
                    "tuition_period_missing",
                    "tuition_period",
                    "tuition amount requires a known period",
                )
            )
        if not _has_evidence(program, "tuition_amount", "tuition_text"):
            issues.append(
                ValidationIssue(
                    "tuition_evidence_missing",
                    "tuition_amount",
                    "tuition requires evidence",
                )
            )

    if program.application_deadline or program.deadline_text:
        if not _has_evidence(program, "application_deadline", "deadline_text"):
            issues.append(
                ValidationIssue(
                    "deadline_evidence_missing",
                    "application_deadline",
                    "deadline requires evidence",
                )
            )

    if program.instruction_languages and not _has_evidence(program, "instruction_languages"):
        issues.append(
            ValidationIssue(
                "language_evidence_missing",
                "instruction_languages",
                "instruction language requires evidence",
            )
        )

    if program.language_requirements is None:
        issues.append(
            ValidationIssue(
                "language_requirement_unknown",
                "language_requirements",
                "language requirement is unknown and needs confirmation",
            )
        )
    elif not _has_evidence(program, "language_requirements"):
        issues.append(
            ValidationIssue(
                "language_requirement_evidence_missing",
                "language_requirements",
                "language requirement requires evidence",
            )
        )

    if program.verification_status == VerificationStatus.VERIFIED and not program.evidence:
        issues.append(
            ValidationIssue(
                "verified_without_evidence",
                "verification_status",
                "verified record cannot have empty evidence",
            )
        )
    return issues


def derive_verification_status(program: Program) -> VerificationStatus:
    """Downgrade incomplete data while preserving explicit conflict and stale states."""
    if program.verification_status in {VerificationStatus.CONFLICTING, VerificationStatus.STALE}:
        return program.verification_status
    if validate_program(program):
        return VerificationStatus.PARTIAL if program.evidence else VerificationStatus.UNVERIFIED
    if not program.evidence:
        return VerificationStatus.UNVERIFIED
    return VerificationStatus.VERIFIED
