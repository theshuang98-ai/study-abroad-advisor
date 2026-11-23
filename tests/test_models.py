import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from study_abroad.models import DegreeLevel, Program, TuitionPeriod, VerificationStatus

NOW = datetime(2026, 11, 21, tzinfo=UTC)


def _program_data(**overrides):
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
        "language_requirements": ["HSK 4 with a score of 210 or better"],
        "academic_requirements": ["Senior high school diploma"],
        "admission_cycle": "2027_entry",
        "verification_status": VerificationStatus.VERIFIED,
        "evidence": [
            {
                "source_id": "xmu_2027_undergraduate_guide",
                "field_name": "tuition_amount",
                "source_url": "https://admissions.xmu.edu.cn/guide",
                "source_quote": "Science and Engineering: RMB 26,000/year.",
                "admission_cycle": "2027_entry",
                "collected_at": NOW,
            }
        ],
        "collected_at": NOW,
    }
    data.update(overrides)
    return data


def test_valid_program_serializes_to_json() -> None:
    program = Program(**_program_data())

    assert program.is_degree_program is True
    assert program.tuition_amount == 26000
    assert program.evidence[0].field_name == "tuition_amount"
    payload = json.loads(program.model_dump_json())
    assert payload["tuition_amount"] == 26000
    assert isinstance(payload["tuition_amount"], int)


def test_fractional_tuition_serializes_as_json_float() -> None:
    program = Program(**_program_data(tuition_amount="26000.50"))

    payload = json.loads(program.model_dump_json())
    assert payload["tuition_amount"] == 26000.5
    assert isinstance(payload["tuition_amount"], float)


def test_required_nullable_fields_must_be_present() -> None:
    data = _program_data()
    del data["tuition_currency"]

    with pytest.raises(ValidationError, match="tuition_currency"):
        Program(**data)


def test_null_values_are_allowed_when_keys_are_present() -> None:
    program = Program(
        **_program_data(
            degree_level=None,
            is_degree_program=None,
            tuition_amount=None,
            tuition_currency=None,
            tuition_period=None,
            instruction_languages=None,
            evidence=[],
            verification_status=VerificationStatus.UNVERIFIED,
        )
    )

    assert program.degree_level is None
    assert program.is_degree_program is None
    assert program.tuition_amount is None
    assert program.instruction_languages is None
    assert program.evidence == []


def test_unexpected_model_fields_are_rejected() -> None:
    with pytest.raises(ValidationError, match="unexpected_fact"):
        Program(**_program_data(unexpected_fact="invented by model"))


def test_negative_tuition_is_rejected() -> None:
    with pytest.raises(ValidationError, match="tuition_amount"):
        Program(**_program_data(tuition_amount="-1"))


def test_empty_evidence_quote_is_rejected() -> None:
    data = _program_data()
    data["evidence"][0]["source_quote"] = "   "

    with pytest.raises(ValidationError, match="source_quote"):
        Program(**data)
