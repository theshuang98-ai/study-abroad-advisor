import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from study_abroad.grounded import GroundedAnswerError, answer_question
from study_abroad.rag import SearchHit


class ToolCallingFakeChatModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _hit() -> SearchHit:
    text = "Long-term Chinese tuition is RMB 21,000 per year."
    return SearchHit(
        chunk_id="nju_hwxy_long_term_chinese:bgc000",
        text=text,
        distance=0.1,
        document_id="nju_hwxy_long_term_chinese",
        program_id=None,
        university="Nanjing University",
        admission_cycle="2027_fall",
        source_url="https://hwxy.nju.edu.cn/guide",
        source_quote=text,
        source_type="web_snapshot",
        collected_at="2026-11-23",
    )


def _model(args: dict) -> ToolCallingFakeChatModel:
    message = AIMessage(
        content="",
        tool_calls=[
            {"name": "GroundedAnswer", "args": args, "id": "call_1", "type": "tool_call"}
        ],
    )
    return ToolCallingFakeChatModel(responses=[message])


def _answer_args(**overrides) -> dict:
    data = {
        "answer": "一学年学费为 21,000 元人民币。",
        "citations": [
            {
                "source_id": "nju_hwxy_long_term_chinese",
                "source_url": "https://hwxy.nju.edu.cn/guide",
                "admission_cycle": "2027_fall",
                "accessed_at": "2026-11-23",
                "quote": "RMB 21,000 per year",
            }
        ],
        "insufficient_evidence": False,
    }
    data.update(overrides)
    return data


def test_answer_keeps_validated_citation() -> None:
    answer = answer_question(_model(_answer_args()), "学费是多少？", [_hit()])

    assert answer.answer.startswith("一学年")
    assert len(answer.citations) == 1
    assert answer.citations[0].source_id == "nju_hwxy_long_term_chinese"


def test_invented_quote_is_rejected() -> None:
    args = _answer_args()
    args["citations"][0]["quote"] = "RMB 99,000 per year"

    with pytest.raises(GroundedAnswerError, match="not supported"):
        answer_question(_model(args), "学费是多少？", [_hit()])


def test_no_hits_returns_refusal_without_model_call() -> None:
    model = ToolCallingFakeChatModel(responses=[])

    answer = answer_question(model, "学费是多少？", [])

    assert answer.insufficient_evidence is True
    assert answer.citations == []
    assert "无法回答" in answer.answer
