import json
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from study_abroad.city_catalog import CityPack
from study_abroad.graph import build_sales_workflow


def _load_city_pack() -> CityPack:
    payload = json.loads(
        Path("data/city_packs/nanjing_pack_v1.json").read_text(encoding="utf-8")
    )
    return CityPack(**payload)


def _intake(hsk_level=None, hsk_score=None) -> dict:
    return {
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
            "hsk_level": hsk_level,
            "hsk_score": hsk_score,
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


def test_sqlite_checkpoint_resumes_clarification_and_review(tmp_path) -> None:
    database = tmp_path / "workflow.sqlite"
    config = {"configurable": {"thread_id": "thread-1"}}

    with SqliteSaver.from_conn_string(str(database)) as saver:
        graph = build_sales_workflow(city_pack=_load_city_pack(), checkpointer=saver)
        first = graph.invoke({"intake": _intake()}, config)

    assert first["__interrupt__"][0].value["missing_fields"] == [
        "language.hsk_level",
        "language.hsk_score",
    ]

    with SqliteSaver.from_conn_string(str(database)) as saver:
        graph = build_sales_workflow(city_pack=_load_city_pack(), checkpointer=saver)
        second = graph.invoke(
            Command(resume={"language.hsk_level": 4, "language.hsk_score": 200}),
            config,
        )
        review = second["__interrupt__"][0].value
        assert review["question"] == "Approve this recommendation report?"
        assert review["report"]["tiers"]

        final = graph.invoke(Command(resume={"approved": True, "notes": "ok"}), config)

    assert final["status"] == "approved"
    assert final["review"] == {"approved": True, "notes": "ok"}


def test_retriever_receives_query_and_result_is_kept() -> None:
    captured: list[str] = []

    def retriever(query: str) -> list[dict]:
        captured.append(query)
        return [{"source_id": "s1", "source_quote": "official quote"}]

    graph = build_sales_workflow(
        city_pack=_load_city_pack(),
        retriever=retriever,
        checkpointer=InMemorySaver(),
    )
    result = graph.invoke(
        {"intake": _intake(hsk_level=4, hsk_score=200)},
        {"configurable": {"thread_id": "thread-2"}},
    )

    assert captured == ["Nanjing one_year_chinese_program"]
    assert result["retrieval"] == [{"source_id": "s1", "source_quote": "official quote"}]


def test_program_without_evidence_gets_flag() -> None:
    pack = _load_city_pack()
    pack.universities[0].official_programs[0].evidence = []
    graph = build_sales_workflow(city_pack=pack, checkpointer=InMemorySaver())

    result = graph.invoke(
        {"intake": _intake(hsk_level=4, hsk_score=200)},
        {"configurable": {"thread_id": "thread-3"}},
    )

    item = result["report"]["tiers"][0]["items"][0]
    assert "no_evidence" in item["flags"]
    assert result["evidence_flags"] == 1
