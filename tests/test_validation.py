from datetime import UTC, datetime

from study_abroad.models import DegreeLevel, Program, TuitionPeriod, VerificationStatus
from study_abroad.validation import derive_verification_status, validate_program

NOW = datetime(2026, 11, 21, tzinfo=UTC)
FIELDS = (
    "degree_level",
    "tuition_amount",
    "application_deadline",
    "instruction_languages",
    "language_requirements",
)


def _evidence(field_name: str) -> dict:
    return {
        "source_id": "xmu_2027_undergraduate_guide",
        "field_name": field_name,
        "source_url": "https://admissions.xmu.edu.cn/guide",
        "source_quote": f"Official evidence for {field_name}",
        "admission_cycle": "2027_entry",
        "collected_at": NOW,
    }


def _program(**overrides) -> Program:
    data = {
        "program_id": "xmu_computer_science_technology",
        "university": "Xiamen University",
        "program_name_original": "Computer Science and Technology",
        "degree_level": DegreeLevel.BACHELOR,
        "is_degree_program": True,
        "academic_field": "Engineering",
        "instruction_languages": ["zh"],
        "duration_text": "4 years",
        "tuition_amount": "26000",
        "tuition_currency": "CNY",
        "tuition_period": TuitionPeriod.YEAR,
        "tuition_text": "RMB 26,000/year",
        "application_deadline": "2027-05-31",
        "deadline_text": "May 31, 2027",
        "language_requirements": ["HSK 4 with 210 or better"],
        "academic_requirements": ["Senior high school diploma"],
        "admission_cycle": "2027_entry",
        "verification_status": VerificationStatus.VERIFIED,
        "evidence": [_evidence(field) for field in FIELDS],
        "collected_at": NOW,
    }
    data.update(overrides)
    return Program(**data)


def _codes(program: Program) -> set[str]:
    return {issue.code for issue in validate_program(program)}


def test_fully_evidenced_program_is_verified() -> None:
    program = _program()

    assert validate_program(program) == []
    assert derive_verification_status(program) == VerificationStatus.VERIFIED


def test_degree_program_requires_matching_level_and_evidence() -> None:
    program = _program(
        degree_level=DegreeLevel.NON_DEGREE,
        evidence=[_evidence("tuition_amount")],
    )

    assert _codes(program) == {
        "degree_level_mismatch",
        "degree_evidence_missing",
        "deadline_evidence_missing",
        "language_evidence_missing",
        "language_requirement_evidence_missing",
    }
    assert derive_verification_status(program) == VerificationStatus.PARTIAL


def test_unknown_degree_cannot_be_verified() -> None:
    program = _program(degree_level=None, is_degree_program=None)

    assert "degree_unknown" in _codes(program)
    assert derive_verification_status(program) == VerificationStatus.PARTIAL


def test_tuition_requires_currency_period_and_evidence() -> None:
    program = _program(
        tuition_currency=None,
        tuition_period=TuitionPeriod.UNKNOWN,
        evidence=[_evidence("degree_level")],
    )

    assert {
        "tuition_currency_missing",
        "tuition_period_missing",
        "tuition_evidence_missing",
    } <= _codes(program)


def test_unknown_language_requirement_blocks_verified_status() -> None:
    program = _program(language_requirements=None)

    assert "language_requirement_unknown" in _codes(program)
    assert derive_verification_status(program) == VerificationStatus.PARTIAL


def test_deadline_requires_evidence() -> None:
    program = _program(evidence=[_evidence("degree_level"), _evidence("tuition_amount")])

    assert "deadline_evidence_missing" in _codes(program)


def test_verified_record_without_evidence_is_downgraded() -> None:
    program = _program(evidence=[])

    assert "verified_without_evidence" in _codes(program)
    assert derive_verification_status(program) == VerificationStatus.UNVERIFIED


def test_conflict_and_stale_states_are_preserved() -> None:
    conflict = _program(verification_status=VerificationStatus.CONFLICTING, evidence=[])
    stale = _program(verification_status=VerificationStatus.STALE, evidence=[])

    assert derive_verification_status(conflict) == VerificationStatus.CONFLICTING
    assert derive_verification_status(stale) == VerificationStatus.STALE
