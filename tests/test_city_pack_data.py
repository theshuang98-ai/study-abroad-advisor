import json
from pathlib import Path

from study_abroad.city_catalog import CityPack

DATA_PATH = Path("data/city_packs/nanjing_pack_v1.json")


def test_nanjing_city_pack_json_loads_into_schema() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    pack = CityPack(**payload)

    assert pack.city_pack_id == "nanjing_pack_v1"
    assert pack.city == "Nanjing"
    assert pack.target_program_type == "one_year_chinese_program"
    assert len(pack.universities) == 4

    university = pack.universities[0]
    assert university.university == "Nanjing University"
    assert university.tier_hint == "reach"
    assert university.pool_status == "active"
    assert len(university.official_programs) == 1

    program = university.official_programs[0]
    assert program.program_id == "nju_2027_one_year_chinese"
    assert program.tuition_amount == 21000
    assert program.requirements.education_level_required == "high_school"
    assert program.evidence[0].source_id == "nju_hwxy_long_term_chinese"
    assert program.verification_status == "partial"

    southeast = pack.universities[1]
    assert southeast.university == "Southeast University"
    assert southeast.pool_status == "active"
    assert len(southeast.official_programs) == 1
    assert southeast.official_programs[0].tuition_amount == 16000
    assert southeast.official_programs[0].application_deadline.isoformat() == "2027-07-30"
    assert len(southeast.official_programs[0].evidence) == 2
    southeast_flags = southeast.official_programs[0].review_flags
    assert "needs_manual_review:admission_cycle" in southeast_flags
    assert "needs_manual_review:education_requirement" in southeast_flags
    assert "needs_manual_review:application_deadline" not in southeast_flags

    hohai = pack.universities[2]
    assert hohai.university == "Hohai University"
    assert hohai.pool_status == "pending"
    assert hohai.official_programs == []
    assert "needs_manual_review:current_cycle_program_page" in hohai.review_flags

    njnu = pack.universities[3]
    assert njnu.university == "Nanjing Normal University"
    assert njnu.pool_status == "active"
    assert len(njnu.official_programs) == 1
    assert njnu.official_programs[0].tuition_amount == 16600
    assert "needs_manual_review:application_deadline" in njnu.official_programs[0].review_flags
