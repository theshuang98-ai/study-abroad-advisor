"""LangGraph pre-sales workflow with clarification and human confirmation."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from study_abroad.city_catalog import CityPack
from study_abroad.schemas import StudentIntake
from study_abroad.workflow import _missing_fields, build_recommendation_report

Retriever = Callable[[str], list[dict[str, Any]]]


class SalesWorkflowState(TypedDict, total=False):
    intake: dict[str, Any]
    missing_fields: list[str]
    clarified: bool
    retrieval: list[dict[str, Any]]
    report: dict[str, Any]
    evidence_flags: int
    review: dict[str, Any]
    status: str


def _set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    target = payload
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value


def build_sales_workflow(
    *,
    city_pack: CityPack,
    retriever: Retriever | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> Any:
    """Compile the workflow; checkpointer is required when running interrupts."""

    def validate(state: SalesWorkflowState) -> dict[str, Any]:
        intake = StudentIntake(**state["intake"])
        return {
            "intake": intake.model_dump(mode="json"),
            "missing_fields": _missing_fields(intake),
        }

    def route_after_validate(state: SalesWorkflowState) -> str:
        if state.get("missing_fields") and not state.get("clarified"):
            return "clarify"
        return "retrieve"

    def clarify(state: SalesWorkflowState) -> dict[str, Any]:
        answers = interrupt(
            {
                "missing_fields": state.get("missing_fields", []),
                "message": "Provide the missing intake fields before generating a report.",
            }
        )
        intake = copy.deepcopy(state["intake"])
        for field, value in answers.items():
            _set_path(intake, field, value)
        return {"intake": intake, "clarified": True}

    def retrieve(state: SalesWorkflowState) -> dict[str, Any]:
        if retriever is None:
            return {"retrieval": []}
        intake = StudentIntake(**state["intake"])
        query = f"{intake.preferred_city} {intake.target_program_type}"
        return {"retrieval": retriever(query)}

    def generate(state: SalesWorkflowState) -> dict[str, Any]:
        report = build_recommendation_report(StudentIntake(**state["intake"]), city_pack)
        return {"report": report.model_dump(mode="json")}

    def check_evidence(state: SalesWorkflowState) -> dict[str, Any]:
        report = copy.deepcopy(state["report"])
        flagged = 0
        for tier in report["tiers"]:
            for item in tier["items"]:
                if not item["evidence"]:
                    item["flags"].append("no_evidence")
                    flagged += 1
        return {"report": report, "evidence_flags": flagged}

    def review(state: SalesWorkflowState) -> dict[str, Any]:
        decision = interrupt(
            {
                "report": state["report"],
                "question": "Approve this recommendation report?",
            }
        )
        approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)
        return {
            "review": decision,
            "status": "approved" if approved else "changes_requested",
        }

    def finalize(state: SalesWorkflowState) -> dict[str, Any]:
        report = copy.deepcopy(state["report"])
        if state.get("status") != "approved":
            for tier in report["tiers"]:
                for item in tier["items"]:
                    item["flags"].append("review_not_approved")
        return {"report": report}

    builder = StateGraph(SalesWorkflowState)
    builder.add_node("validate", validate)
    builder.add_node("clarify", clarify)
    builder.add_node("retrieve", retrieve)
    builder.add_node("generate", generate)
    builder.add_node("check_evidence", check_evidence)
    builder.add_node("review", review)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "validate")
    builder.add_conditional_edges(
        "validate",
        route_after_validate,
        {"clarify": "clarify", "retrieve": "retrieve"},
    )
    builder.add_edge("clarify", "validate")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "check_evidence")
    builder.add_edge("check_evidence", "review")
    builder.add_edge("review", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)
