from study_abroad.answer_eval import evaluate_answers
from study_abroad.grounded import Citation, GroundedAnswer, GroundedAnswerError


class _Index:
    def search(self, query: str, *, k: int):
        return []


def _answer(source_id: str | None, insufficient: bool) -> GroundedAnswer:
    citations = []
    if source_id is not None:
        citations.append(
            Citation(
                source_id=source_id,
                source_url="https://example.edu/guide",
                admission_cycle="2027_fall",
                accessed_at="2026-11-23",
                quote="quote",
            )
        )
    return GroundedAnswer(
        answer="answer",
        citations=citations,
        insufficient_evidence=insufficient,
    )


def test_answer_eval_measures_citations_and_refusals(monkeypatch) -> None:
    answers = {
        "q1": _answer("s1", False),
        "q2": _answer(None, True),
        "q3": _answer(None, True),
    }
    monkeypatch.setattr(
        "study_abroad.answer_eval.answer_question",
        lambda model, question, hits: answers[question],
    )
    cases = [
        {"case_id": "c1", "question": "q1", "expected_source_ids": ["s1"]},
        {
            "case_id": "c2",
            "question": "q2",
            "expected_source_ids": ["s2"],
            "expect_insufficient": True,
        },
        {"case_id": "c3", "question": "q3", "expected_source_ids": ["s1"]},
    ]

    summary = evaluate_answers(object(), _Index(), cases)

    assert summary.total == 3
    assert summary.citation_hits == 1
    assert summary.citation_complete == 1
    assert summary.refusal_expected == 1
    assert summary.refusal_correct == 2
    assert summary.errors == 0


def test_answer_eval_records_case_error(monkeypatch) -> None:
    def fail(model, question, hits):
        raise GroundedAnswerError("invented citation")

    monkeypatch.setattr("study_abroad.answer_eval.answer_question", fail)
    cases = [{"case_id": "c1", "question": "q1", "expected_source_ids": ["s1"]}]

    summary = evaluate_answers(object(), _Index(), cases)

    assert summary.errors == 1
    assert summary.citation_hits == 0
    assert summary.results[0].error.startswith("GroundedAnswerError")
