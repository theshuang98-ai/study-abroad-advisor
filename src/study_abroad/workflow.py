"""Minimal pre-sales recommendation workflow."""

from __future__ import annotations

from datetime import UTC, datetime

from study_abroad.city_catalog import CityPack, ProgramEntry
from study_abroad.schemas import (
    EvidenceRef,
    RecommendationReport,
    StudentIntake,
    Tier,
    TierItem,
)


class WorkflowInputError(ValueError):
    """Raised when the intake cannot be used for report generation."""


def _missing_fields(intake: StudentIntake) -> list[str]:
    missing: list[str] = []
    if intake.language.hsk_level is None:
        missing.append("language.hsk_level")
    if intake.language.hsk_score is None:
        missing.append("language.hsk_score")
    if intake.constraints.annual_budget_cny is None:
        missing.append("constraints.annual_budget_cny")
    return missing


def _to_evidence_ref(item) -> EvidenceRef:
    return EvidenceRef(
        source_id=item.source_id,
        source_url=item.source_url,
        source_title=item.source_title,
        source_quote=item.source_quote,
        admission_cycle=item.admission_cycle,
        accessed_at=item.accessed_at,
    )


def _budget_flags(program: ProgramEntry, budget: float | None) -> list[str]:
    if budget is None or program.tuition_amount is None:
        return []
    if program.tuition_currency != "CNY" or program.tuition_period != "year":
        return ["budget_check_skipped"]
    if program.tuition_amount > budget:
        return ["over_budget"]
    return []


def _language_flags(intake: StudentIntake, program: ProgramEntry) -> list[str]:
    """Compare published language requirements with the student's declared scores."""
    flags: list[str] = []
    required = program.requirements
    language = intake.language

    if required.hsk_level_required is not None:
        if language.hsk_level is None:
            flags.append("hsk_level_unknown")
        elif language.hsk_level < required.hsk_level_required:
            flags.append("hsk_level_below_required")

    if required.hsk_score_required is not None:
        if language.hsk_score is None:
            flags.append("hsk_score_unknown")
        elif language.hsk_score < required.hsk_score_required:
            flags.append("hsk_score_below_required")

    if required.ielts_score_required is not None:
        if language.ielts_score is None:
            flags.append("ielts_score_unknown")
        elif language.ielts_score < required.ielts_score_required:
            flags.append("ielts_score_below_required")

    if required.toefl_score_required is not None:
        if language.toefl_score is None:
            flags.append("toefl_score_unknown")
        elif language.toefl_score < required.toefl_score_required:
            flags.append("toefl_score_below_required")

    return flags


def _to_tier_item(
    program: ProgramEntry,
    tier_hint: str,
    intake: StudentIntake,
) -> TierItem:
    flags: list[str] = []
    flags.extend(_budget_flags(program, intake.constraints.annual_budget_cny))
    flags.extend(_language_flags(intake, program))
    if program.admission_cycle.casefold() != intake.target_intake_cycle.casefold():
        flags.append("admission_cycle_mismatch")
    if program.verification_status != "verified":
        flags.append(program.verification_status)
    flags.extend(program.review_flags)

    return TierItem(
        university=program.university,
        city=program.city,
        program_name=program.program_name,
        program_type=program.program_type,
        instruction_language=program.instruction_language,
        duration_text=program.duration_text,
        tuition_amount=program.tuition_amount,
        tuition_currency=program.tuition_currency,
        tuition_period=program.tuition_period,
        application_deadline=program.application_deadline,
        requirement_summary=[
            value
            for value in [
                program.requirements.education_level_required,
                program.requirements.chinese_level_required,
                *program.requirements.other_requirements,
            ]
            if value
        ],
        fit_summary=f"Placed in {tier_hint} tier based on current catalog information.",
        flags=flags,
        evidence=[_to_evidence_ref(item) for item in program.evidence],
    )


def _tier_label(tier_name: str) -> str:
    labels = {
        "reach": "冲刺档",
        "match": "匹配档",
        "safety": "保底档",
    }
    return labels.get(tier_name, tier_name)


def build_recommendation_report(
    intake: StudentIntake,
    city_pack: CityPack,
) -> RecommendationReport:
    """Build a first-pass recommendation table from a city pack."""
    if intake.preferred_city.casefold() != city_pack.city.casefold():
        raise WorkflowInputError("preferred_city does not match city_pack.city")
    if intake.target_program_type != city_pack.target_program_type:
        raise WorkflowInputError("target_program_type does not match city_pack")

    grouped: dict[str, list[TierItem]] = {"reach": [], "match": [], "safety": []}
    excluded = {name.casefold() for name in intake.preferences.excluded_universities}

    for university in city_pack.universities:
        if university.pool_status != "active":
            continue
        if university.university.casefold() in excluded:
            continue
        tier_hint = university.tier_hint
        if tier_hint not in grouped:
            grouped[tier_hint] = []
        for program in university.official_programs:
            grouped[tier_hint].append(_to_tier_item(program, tier_hint, intake))

    tiers = [
        Tier(tier_name=name, tier_label=_tier_label(name), items=items)
        for name, items in grouped.items()
        if items
    ]
    missing = _missing_fields(intake)

    return RecommendationReport(
        report_id=f"report_{intake.intake_id}",
        intake_id=intake.intake_id,
        city=city_pack.city,
        target_program_type=city_pack.target_program_type,
        generated_at=datetime.now(UTC),
        summary=(
            f"Initial recommendation table for {intake.preferred_city} "
            f"{city_pack.target_program_type} consultation."
        ),
        tiers=tiers,
        missing_fields=missing,
        disclaimer=(
            "This report is for pre-sales consultation only and is not an "
            "admission decision."
        ),
    )
