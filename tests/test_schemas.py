import pytest
from pydantic import ValidationError

from study_abroad.schemas import RecommendationReport, StudentIntake


def _intake(**overrides):
    data = {
        "intake_id": "intake_1",
        "student_ref": None,
        "preferred_city": "Nanjing",
        "backup_cities": ["Suzhou"],
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
    return data


def _report(**overrides):
    data = {
        "report_id": "report_1",
        "intake_id": "intake_1",
        "city": "Nanjing",
        "target_program_type": "one_year_chinese_program",
        "generated_at": "2026-11-23T10:05:00Z",
        "summary": "Initial recommendation table for consultation.",
        "tiers": [
            {
                "tier_name": "reach",
                "tier_label": "冲刺档",
                "items": [
                    {
                        "university": "Nanjing University",
                        "city": "Nanjing",
                        "program_name": "One-Year Chinese Language Program",
                        "program_type": "one_year_chinese_program",
                        "instruction_language": "Chinese",
                        "duration_text": "1 year",
                        "tuition_amount": 26000,
                        "tuition_currency": "CNY",
                        "tuition_period": "year",
                        "application_deadline": "2027-06-30",
                        "requirement_summary": ["High school diploma or equivalent"],
                        "fit_summary": "Placed in reach tier for initial consultation.",
                        "flags": ["needs_manual_review"],
                        "evidence": [
                            {
                                "source_id": "nju_2027_chinese_program",
                                "source_url": "https://example.edu/nju",
                                "source_title": "Nanjing University Chinese Program",
                                "source_quote": (
                                    "One-year Chinese language program for "
                                    "international students."
                                ),
                                "admission_cycle": "2027_fall",
                                "accessed_at": "2026-11-23",
                            }
                        ],
                    }
                ],
            }
        ],
        "missing_fields": ["hsk_level", "hsk_score"],
        "disclaimer": (
            "This report is for pre-sales consultation only and is not an "
            "admission decision."
        ),
    }
    data.update(overrides)
    return data


def test_student_intake_schema_is_valid() -> None:
    intake = StudentIntake(**_intake())

    assert intake.preferred_city == "Nanjing"
    assert intake.language.hsk_level is None
    assert intake.constraints.needs_dormitory is True


def test_recommendation_report_schema_is_valid() -> None:
    report = RecommendationReport(**_report())

    assert report.city == "Nanjing"
    assert report.tiers[0].items[0].university == "Nanjing University"
    assert report.tiers[0].items[0].evidence[0].source_id == "nju_2027_chinese_program"


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        StudentIntake(**_intake(unexpected_field="x"))


def test_invalid_enum_is_rejected() -> None:
    data = _intake()
    data["education"]["graduation_status"] = "unknown_status"

    with pytest.raises(ValidationError):
        StudentIntake(**data)
