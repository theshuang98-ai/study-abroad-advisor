import json
from pathlib import Path

import pytest

from study_abroad.city_catalog import CityPack
from study_abroad.schemas import StudentIntake
from study_abroad.workflow import WorkflowInputError, build_recommendation_report


def _load_city_pack() -> CityPack:
    payload = json.loads(
        Path("data/city_packs/nanjing_pack_v1.json").read_text(encoding="utf-8")
    )
    return CityPack(**payload)


def _intake(**overrides):
    data = {
        "intake_id": "intake_1",
        "student_ref": None,
        "preferred_city": "Nanjing",
        "backup_cities": [],
        "target_program_type": "one_year_chinese_program",
        "target_intake_cycle": "2027_fall",
        "created_at": "2026-11-23T10:00:00Z",
        "education": {
            "current_education_level": "high_school",
            "graduation_status": "expected_graduation",
            "school_name": "Hanoi High School",
            "gpa_or_ranking": "top 20%",
        },
        "language": {
            "native_language": "Vietnamese",
            "chinese_level": "beginner",
            "hsk_level": None,
            "hsk_score": None,
            "ielts_score": 6.0,
            "toefl_score": None,
            "other_language_cert": None,
        },
        "constraints": {
            "annual_budget_cny": 30000,
            "preferred_school_tiers": ["reach", "match", "safety"],
            "preferred_campus_type": "no_preference",
            "needs_dormitory": True,
        },
        "preferences": {
            "preferred_universities": [],
            "excluded_universities": [],
            "priority_ranking": ["city", "school_tier", "cost"],
            "special_notes": None,
        },
    }
    data.update(overrides)
    return StudentIntake(**data)


def test_build_recommendation_report_from_city_pack() -> None:
    report = build_recommendation_report(_intake(), _load_city_pack())

    assert report.intake_id == "intake_1"
    assert report.city == "Nanjing"
    assert [tier.tier_name for tier in report.tiers] == ["reach", "match", "safety"]
    assert report.tiers[0].items[0].university == "Nanjing University"
    assert report.tiers[0].items[1].university == "Southeast University"
    assert report.tiers[1].items[0].university == "Hohai University"
    assert report.tiers[1].items[1].university == "Nanjing Normal University"
    assert report.tiers[2].items[0].university == "Nanjing Tech University"
    assert "needs_manual_review:education_requirement" in report.tiers[0].items[1].flags
    assert report.missing_fields == [
        "language.hsk_level",
        "language.hsk_score",
    ]


def test_mismatched_city_is_rejected() -> None:
    intake = _intake(preferred_city="Chengdu")

    with pytest.raises(WorkflowInputError, match="preferred_city"):
        build_recommendation_report(intake, _load_city_pack())


def test_over_budget_program_gets_flag() -> None:
    intake = _intake()
    intake.constraints.annual_budget_cny = 20000

    report = build_recommendation_report(intake, _load_city_pack())

    assert "over_budget" in report.tiers[0].items[0].flags


def test_language_requirement_flags_come_from_catalog_fields() -> None:
    pack = _load_city_pack()
    program = pack.universities[0].official_programs[0]
    program.requirements.hsk_level_required = 4
    program.requirements.hsk_score_required = 180
    intake = _intake()
    intake.language.hsk_level = 3
    intake.language.hsk_score = None

    report = build_recommendation_report(intake, pack)

    flags = report.tiers[0].items[0].flags
    assert "hsk_level_below_required" in flags
    assert "hsk_score_unknown" in flags


def test_budget_check_is_skipped_for_non_cny_or_non_year_tuition() -> None:
    pack = _load_city_pack()
    pack.universities[0].official_programs[0].tuition_currency = "USD"

    report = build_recommendation_report(_intake(), pack)

    assert "budget_check_skipped" in report.tiers[0].items[0].flags


def test_excluded_university_is_omitted() -> None:
    intake = _intake()
    intake.preferences.excluded_universities = ["Nanjing University"]

    report = build_recommendation_report(intake, _load_city_pack())

    universities = [item.university for tier in report.tiers for item in tier.items]
    assert "Nanjing University" not in universities
