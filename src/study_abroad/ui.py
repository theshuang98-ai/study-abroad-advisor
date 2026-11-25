"""Pure helpers for the Streamlit pre-sales UI."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CITY = "Nanjing"
DEFAULT_PROGRAM_TYPE = "one_year_chinese_program"
DEFAULT_CYCLE = "2027_fall"


def build_intake(
    *,
    intake_id: str,
    education_level: str,
    graduation_status: str,
    native_language: str,
    chinese_level: str | None,
    hsk_level: int | None,
    hsk_score: int | None,
    ielts_score: float | None,
    annual_budget_cny: float | None,
    needs_dormitory: bool,
    preferred_tiers: list[str],
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable StudentIntake payload for the graph."""
    timestamp = created_at or datetime.now(UTC)
    return {
        "intake_id": intake_id,
        "student_ref": None,
        "preferred_city": DEFAULT_CITY,
        "backup_cities": [],
        "target_program_type": DEFAULT_PROGRAM_TYPE,
        "target_intake_cycle": DEFAULT_CYCLE,
        "created_at": timestamp.isoformat(),
        "education": {
            "current_education_level": education_level,
            "graduation_status": graduation_status,
            "school_name": None,
            "gpa_or_ranking": None,
        },
        "language": {
            "native_language": native_language,
            "chinese_level": chinese_level,
            "hsk_level": hsk_level,
            "hsk_score": hsk_score,
            "ielts_score": ielts_score,
            "toefl_score": None,
            "other_language_cert": None,
        },
        "constraints": {
            "annual_budget_cny": annual_budget_cny,
            "preferred_school_tiers": preferred_tiers,
            "preferred_campus_type": "no_preference",
            "needs_dormitory": needs_dormitory,
        },
        "preferences": {
            "preferred_universities": [],
            "excluded_universities": [],
            "priority_ranking": ["city", "school_tier", "cost"],
            "special_notes": None,
        },
    }


def load_env_file(path: str | Path) -> None:
    """Load KEY=VALUE pairs without overriding existing environment variables."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def report_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a report into one row per program, keeping the tier label."""
    rows: list[dict[str, Any]] = []
    for tier in report.get("tiers", []):
        for item in tier.get("items", []):
            rows.append(
                {
                    **item,
                    "tier_name": tier.get("tier_name", ""),
                    "tier_label": tier.get("tier_label", ""),
                }
            )
    return rows
