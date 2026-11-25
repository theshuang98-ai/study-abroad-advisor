import os
from datetime import UTC, datetime

from study_abroad.schemas import StudentIntake
from study_abroad.ui import build_intake, load_env_file, report_items


def test_build_intake_matches_student_schema() -> None:
    payload = build_intake(
        intake_id="intake_1",
        education_level="high_school",
        graduation_status="expected_graduation",
        native_language="Vietnamese",
        chinese_level="beginner",
        hsk_level=4,
        hsk_score=210,
        ielts_score=6.0,
        annual_budget_cny=30000,
        needs_dormitory=True,
        preferred_tiers=["reach", "match", "safety"],
        created_at=datetime(2026, 11, 24, tzinfo=UTC),
    )

    intake = StudentIntake(**payload)
    assert intake.preferred_city == "Nanjing"
    assert intake.language.hsk_score == 210
    assert intake.constraints.annual_budget_cny == 30000
    assert payload["created_at"] == "2026-11-24T00:00:00+00:00"


def test_load_env_file_does_not_override_existing(monkeypatch, tmp_path) -> None:
    path = tmp_path / ".env"
    path.write_text("DEEPSEEK_API_KEY='from-file'\n# comment\n", encoding="utf-8")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    load_env_file(path)
    assert os.environ["DEEPSEEK_API_KEY"] == "from-file"

    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-shell")
    load_env_file(path)
    assert os.environ["DEEPSEEK_API_KEY"] == "from-shell"


def test_report_items_flattens_tiers() -> None:
    report = {
        "tiers": [
            {
                "tier_name": "reach",
                "tier_label": "冲刺档",
                "items": [{"university": "Nanjing University"}],
            },
            {
                "tier_name": "match",
                "tier_label": "匹配档",
                "items": [{"university": "Nanjing Normal University"}],
            },
        ]
    }

    rows = report_items(report)

    assert [row["university"] for row in rows] == [
        "Nanjing University",
        "Nanjing Normal University",
    ]
    assert rows[0]["tier_label"] == "冲刺档"
