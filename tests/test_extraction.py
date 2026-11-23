from datetime import UTC, datetime

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from study_abroad.extraction import ExtractionError, extract_program, extract_programs
from study_abroad.models import Program, VerificationStatus

NOW = datetime(2026, 11, 21, tzinfo=UTC)
SOURCE = {
    "source_id": "xmu_2027_undergraduate_guide",
    "university": "Xiamen University",
    "url": "https://admissions.xmu.edu.cn/guide",
    "admission_cycle": "2027_entry",
}
TEXT = (
    "Computer Science and Technology is a 4-year bachelor program. "
    "Tuition is RMB 26,000/year. The language of instruction is Chinese. "
    "HSK 4 with 210 or better is required. "
    "The application deadline is May 31, 2027."
)


class ToolCallingFakeChatModel(FakeMessagesListChatModel):
    """Minimal fake that enables LangChain's function-calling output path."""

    def bind_tools(self, tools, **kwargs):
        return self


def _evidence(field_name: str, quote: str, **overrides) -> dict:
    data = {
        "source_id": SOURCE["source_id"],
        "field_name": field_name,
        "source_url": SOURCE["url"],
        "source_quote": quote,
        "admission_cycle": "2027_entry",
        "collected_at": "2026-11-01T00:00:00Z",
    }
    data.update(overrides)
    return data


def _program_args(**overrides) -> dict:
    data = {
        "program_id": "xmu_computer_science_technology",
        "university": SOURCE["university"],
        "program_name_original": "Computer Science and Technology",
        "degree_level": "bachelor",
        "is_degree_program": True,
        "academic_field": "Engineering",
        "instruction_languages": ["zh"],
        "duration_text": "4-year",
        "tuition_amount": 26000,
        "tuition_currency": "CNY",
        "tuition_period": "year",
        "tuition_text": "RMB 26,000/year",
        "application_deadline": "2027-05-31",
        "deadline_text": "May 31, 2027",
        "language_requirements": ["HSK 4 with 210 or better"],
        "academic_requirements": None,
        "admission_cycle": "2027_entry",
        "verification_status": "verified",
        "evidence": [
            _evidence("degree_level", "4-year bachelor program"),
            _evidence("tuition_amount", "Tuition is RMB 26,000/year"),
            _evidence("application_deadline", "The application deadline is May 31, 2027"),
            _evidence("instruction_languages", "The language of instruction is Chinese"),
            _evidence("language_requirements", "HSK 4 with 210 or better is required"),
        ],
        "collected_at": "2026-11-01T00:00:00Z",
    }
    data.update(overrides)
    return data


def _model(args: dict) -> ToolCallingFakeChatModel:
    message = AIMessage(
        content="",
        tool_calls=[{"name": "Program", "args": args, "id": "call_1", "type": "tool_call"}],
    )
    return ToolCallingFakeChatModel(responses=[message])


def test_extract_program_uses_langchain_structured_output() -> None:
    program = extract_program(_model(_program_args()), SOURCE, TEXT, collected_at=NOW)

    assert isinstance(program, Program)
    assert program.program_id == "xmu_computer_science_technology"
    assert program.tuition_amount == 26000
    assert program.verification_status == VerificationStatus.VERIFIED
    assert program.collected_at == NOW


def test_evidence_cannot_point_to_another_source() -> None:
    args = _program_args()
    args["evidence"][0]["source_id"] = "invented_source"

    with pytest.raises(ExtractionError, match="different source"):
        extract_program(_model(args), SOURCE, TEXT, collected_at=NOW)


def test_evidence_quote_must_exist_in_source_text() -> None:
    args = _program_args()
    args["evidence"][0]["source_quote"] = "Tuition is free for everyone"

    with pytest.raises(ExtractionError, match="not present in source"):
        extract_program(_model(args), SOURCE, TEXT, collected_at=NOW)


def test_empty_or_oversized_source_is_rejected() -> None:
    model = _model(_program_args())

    with pytest.raises(ValueError, match="must not be empty"):
        extract_program(model, SOURCE, "  ", collected_at=NOW)
    with pytest.raises(ValueError, match="too large"):
        extract_program(model, SOURCE, "x" * 40_001, collected_at=NOW)


def test_batch_extracts_multiple_sources_and_keeps_valid_results() -> None:
    catalog_source = {
        "source_id": "xmu_catalog",
        "university": SOURCE["university"],
        "url": "https://admissions.xmu.edu.cn/catalog",
        "admission_cycle": "2027_entry",
    }
    candidates = [
        {"candidate_id": "xmu_catalog#r1", "source_id": "xmu_catalog", "text": "Row 1"},
        {"candidate_id": "xmu_catalog#r2", "source_id": "xmu_catalog", "text": "Row 2"},
        {"candidate_id": "xmu_catalog#r3", "source_id": "xmu_catalog", "text": "Row 3"},
    ]
    good_args = _program_args()
    bad_args = _program_args()
    bad_args["evidence"][0]["source_quote"] = "Quote absent from the guide"
    responses = [
        AIMessage(
            content="",
            tool_calls=[{"name": "Program", "args": args, "id": f"call_{i}", "type": "tool_call"}],
        )
        for i, args in enumerate([good_args, bad_args, good_args], start=1)
    ]
    received_inputs = []

    class RecordingFakeChatModel(ToolCallingFakeChatModel):
        def invoke(self, input, config=None, **kwargs):
            received_inputs.append(str(input))
            return super().invoke(input, config, **kwargs)

    model = RecordingFakeChatModel(responses=responses)

    result = extract_programs(
        model,
        candidates,
        [SOURCE, catalog_source],
        {SOURCE["source_id"]: TEXT},
        collected_at=NOW,
    )

    assert [program.program_id for program in result.programs] == [
        "xmu_catalog#r1",
        "xmu_catalog#r3",
    ]
    assert len(result.failures) == 1
    assert result.failures[0].candidate_id == "xmu_catalog#r2"
    assert all(
        program.verification_status == VerificationStatus.VERIFIED
        for program in result.programs
    )
    assert len(received_inputs) == 3
    assert all("Tuition is RMB 26,000/year" in prompt for prompt in received_inputs)
    assert all("The application deadline is May 31, 2027" in prompt for prompt in received_inputs)
