from study_abroad.catalog_validation import CatalogSource, validate_catalog_evidence
from study_abroad.city_catalog import (
    CityPack,
    ProgramEntry,
    ProgramRequirements,
    UniversityEntry,
)


def _program(**overrides):
    data = {
        "program_id": "nju_chinese",
        "university": "Nanjing University",
        "city": "Nanjing",
        "program_name": "Long-Term Chinese Language Program",
        "program_type": "one_year_chinese_program",
        "admission_cycle": "2027_fall",
        "instruction_language": "Chinese",
        "duration_text": "1 year",
        "tuition_amount": 21000,
        "tuition_currency": "CNY",
        "tuition_period": "year",
        "application_deadline": "2027-06-25",
        "requirements": ProgramRequirements(
            education_level_required="high_school",
            chinese_level_required=None,
            hsk_level_required=None,
            hsk_score_required=None,
            ielts_score_required=None,
            toefl_score_required=None,
            other_requirements=[],
        ),
        "evidence": [],
        "verification_status": "verified",
        "review_flags": [],
        "last_reviewed_at": None,
    }
    data.update(overrides)
    return ProgramEntry(**data)


def _pack(program):
    return CityPack(
        city_pack_id="nanjing_pack_v1",
        city="Nanjing",
        country="China",
        target_program_type="one_year_chinese_program",
        admission_cycle="2027_fall",
        version="v1",
        created_at="2026-11-23T10:00:00Z",
        updated_at="2026-11-23T10:00:00Z",
        universities=[
            UniversityEntry(
                university="Nanjing University",
                city="Nanjing",
                tier_hint="reach",
                pool_status="active",
                review_flags=[],
                official_programs=[program],
            )
        ],
    )


def test_valid_evidence_has_no_issues() -> None:
    program = _program(
        evidence=[
            {
                "source_id": "nju_source",
                "source_url": "https://example.edu/nju",
                "source_title": "NJU Chinese Program",
                "source_quote": "学费：一学年 21000 元。",
                "admission_cycle": "2027_fall",
                "accessed_at": "2026-11-23",
            }
        ]
    )
    sources = {
        "nju_source": CatalogSource(
            source_id="nju_source",
            url="https://example.edu/nju",
            text="长期汉语进修项目\n学费：一学年 21000 元。",
        )
    }

    assert validate_catalog_evidence(_pack(program), sources) == []


def test_missing_source_is_reported() -> None:
    program = _program(
        evidence=[
            {
                "source_id": "missing_source",
                "source_url": "https://example.edu/nju",
                "source_title": "NJU",
                "source_quote": "学费：一学年 21000 元。",
                "admission_cycle": "2027_fall",
                "accessed_at": "2026-11-23",
            }
        ]
    )

    issues = validate_catalog_evidence(_pack(program), {})

    assert [issue.code for issue in issues] == ["source_not_found"]


def test_url_and_quote_mismatches_are_reported() -> None:
    program = _program(
        evidence=[
            {
                "source_id": "nju_source",
                "source_url": "https://evil.example/nju",
                "source_title": "NJU",
                "source_quote": "不存在的原文",
                "admission_cycle": "2027_fall",
                "accessed_at": "2026-11-23",
            }
        ]
    )
    sources = {
        "nju_source": CatalogSource(
            source_id="nju_source",
            url="https://example.edu/nju",
            text="学费：一学年 21000 元。",
        )
    }

    issues = validate_catalog_evidence(_pack(program), sources)
    codes = [issue.code for issue in issues]

    assert codes == ["source_url_mismatch", "quote_not_found"]


def test_active_program_without_evidence_is_reported() -> None:
    issues = validate_catalog_evidence(_pack(_program()), {})

    assert [issue.code for issue in issues] == ["evidence_missing"]
