import json
from pathlib import Path

from study_abroad.city_catalog import CityPack

CASES_PATH = Path("evals/nanjing_cases.json")
PACK_PATH = Path("data/city_packs/nanjing_pack_v1.json")
SOURCES_PATH = Path("data/city_packs/nanjing_sources.json")


def test_nanjing_retrieval_cases_have_valid_references() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    pack = CityPack(**json.loads(PACK_PATH.read_text(encoding="utf-8")))
    source_ids = {
        source["source_id"]
        for source in json.loads(SOURCES_PATH.read_text(encoding="utf-8"))["sources"]
    }
    program_ids = {
        program.program_id
        for university in pack.universities
        for program in university.official_programs
    }

    assert 10 <= len(cases) <= 20
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert all(case["expected_source_ids"] for case in cases)
    assert all(set(case["expected_source_ids"]) <= source_ids for case in cases)
    assert all(set(case["expected_program_ids"]) <= program_ids for case in cases)
    assert all(case["question"] and case["expected_answer"] for case in cases)
