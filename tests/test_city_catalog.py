import pytest
from pydantic import ValidationError

from study_abroad.city_catalog import CityPack, ProgramEntry


def _requirements(**overrides):
    data = {
        "education_level_required": "high_school",
        "chinese_level_required": "beginner_or_above",
        "hsk_level_required": None,
        "hsk_score_required": None,
        "ielts_score_required": None,
        "toefl_score_required": None,
        "other_requirements": ["International students"],
    }
    data.update(overrides)
    return data


def _program(**overrides):
    data = {
        "program_id": "nju_2027_one_year_chinese",
        "university": "Nanjing University",
        "city": "Nanjing",
        "program_name": "One-Year Chinese Language Program",
        "program_type": "one_year_chinese_program",
        "admission_cycle": "2027_fall",
        "instruction_language": "Chinese",
        "duration_text": "1 year",
        "tuition_amount": 26000,
        "tuition_currency": "CNY",
        "tuition_period": "year",
        "application_deadline": "2027-06-30",
        "requirements": _requirements(),
        "evidence": [
            {
                "source_id": "nju_2027_chinese_program",
                "source_url": "https://example.edu/nju",
                "source_title": "Nanjing University Chinese Program",
                "source_quote": "One-year Chinese language program for international students.",
                "admission_cycle": "2027_fall",
                "accessed_at": "2026-11-23",
            }
        ],
        "verification_status": "partial",
        "review_flags": ["needs_manual_review:application_deadline"],
        "last_reviewed_at": "2026-11-23T10:00:00Z",
    }
    data.update(overrides)
    return data


def _city_pack(**overrides):
    data = {
        "city_pack_id": "nanjing_pack_v1",
        "city": "Nanjing",
        "country": "China",
        "target_program_type": "one_year_chinese_program",
        "admission_cycle": "2027_fall",
        "version": "v1",
        "created_at": "2026-11-23T10:00:00Z",
        "updated_at": "2026-11-23T10:00:00Z",
        "universities": [
            {
                "university": "Nanjing University",
                "city": "Nanjing",
                "tier_hint": "reach",
                "pool_status": "active",
                "review_flags": [],
                "official_programs": [_program()],
            }
        ],
    }
    data.update(overrides)
    return data


def test_city_pack_schema_is_valid() -> None:
    pack = CityPack(**_city_pack())

    assert pack.city == "Nanjing"
    assert pack.universities[0].tier_hint == "reach"
    assert pack.universities[0].official_programs[0].program_id == "nju_2027_one_year_chinese"


def test_program_entry_schema_is_valid() -> None:
    program = ProgramEntry(**_program())

    assert program.university == "Nanjing University"
    assert program.tuition_amount == 26000
    assert program.evidence[0].source_id == "nju_2027_chinese_program"


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CityPack(**_city_pack(unexpected_field="x"))


def test_invalid_verification_status_is_rejected() -> None:
    program = _program(verification_status="almost_verified")

    with pytest.raises(ValidationError):
        ProgramEntry(**program)
