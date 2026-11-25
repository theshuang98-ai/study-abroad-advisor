"""Streamlit demo for the Nanjing pre-sales recommendation workbench."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path

import streamlit as st
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from study_abroad.city_catalog import CityPack
from study_abroad.graph import build_sales_workflow
from study_abroad.grounded import GroundedAnswerError, answer_question
from study_abroad.llm import MissingAPIKeyError, load_deepseek_chat_model
from study_abroad.nanjing_eval import build_nanjing_retriever
from study_abroad.ui import build_intake, load_env_file

ROOT = Path(__file__).resolve().parents[2]

PACK_PATH = ROOT / "data/city_packs/nanjing_pack_v1.json"
SOURCES_PATH = ROOT / "data/city_packs/nanjing_sources.json"
CHROMA_PATH = ROOT / ".local/runtime/chroma_nanjing_bge_final"
MODEL_PATH = ROOT / ".local/models/bge-m3"
CHECKPOINT_PATH = ROOT / ".local/runtime/streamlit_checkpoints.sqlite"

load_env_file(ROOT / ".env")

st.set_page_config(page_title="南京汉语项目售前工作台", page_icon="🎓", layout="wide")


@st.cache_resource(show_spinner=False)
def get_city_pack() -> CityPack:
    return CityPack(**json.loads(PACK_PATH.read_text(encoding="utf-8")))


@st.cache_resource(show_spinner=False)
def get_source_titles() -> dict[str, str]:
    payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    return {source["source_id"]: source["title"] for source in payload["sources"]}


@st.cache_resource(show_spinner=False)
def get_retriever():
    return build_nanjing_retriever(
        model_path=MODEL_PATH,
        persist_directory=CHROMA_PATH,
        device=os.environ.get("EMBEDDING_DEVICE", "cuda"),
        k=4,
    )


def lazy_retriever(query: str) -> list[dict]:
    return get_retriever()(query)


@st.cache_resource(show_spinner=False)
def get_workflow():
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(CHECKPOINT_PATH), check_same_thread=False)
    saver = SqliteSaver(connection)
    return build_sales_workflow(
        city_pack=get_city_pack(),
        retriever=lazy_retriever,
        checkpointer=saver,
    )


def _tuition(item: dict) -> str:
    amount = item.get("tuition_amount")
    if amount is None:
        return "官网未列明"
    currency = item.get("tuition_currency") or ""
    period = item.get("tuition_period") or ""
    return f"{amount:,.0f} {currency}/{period}".strip()


def _render_report(report: dict) -> None:
    st.subheader("推荐表")
    st.caption(report.get("summary", ""))
    for tier in report.get("tiers", []):
        st.markdown(f"### {tier['tier_label']}")
        for item in tier["items"]:
            with st.expander(f"{item['university']} · {item['program_name']}"):
                left, middle, right = st.columns(3)
                left.metric("学费", _tuition(item))
                middle.metric("截止日期", item.get("application_deadline") or "未列明")
                right.metric("状态", ", ".join(item["flags"]) or "无标记")
                if item.get("requirement_summary"):
                    st.write("**官网要求**：" + "；".join(item["requirement_summary"]))
                if item["evidence"]:
                    st.write("**证据**")
                    for evidence in item["evidence"]:
                        st.markdown(
                            f"- [{evidence['source_title']}]({evidence['source_url']})"
                            f" · {evidence['admission_cycle']} · 采集 {evidence['accessed_at']}"
                        )
                        st.caption(f"> {evidence['source_quote']}")


def _render_review(result: dict, config: dict) -> None:
    status = result.get("status")
    if status:
        if status == "approved":
            st.success("报告已批准。")
        else:
            st.warning("报告被退回，相关项目已加 `review_not_approved` 标记。")
        return

    interrupts = result.get("__interrupt__") or ()
    if not interrupts:
        return
    value = interrupts[0].value
    if "missing_fields" in value:
        st.warning("还缺字段：" + ", ".join(value["missing_fields"]))
        return

    st.info("请审核推荐表。批准后才会写入最终状态。")
    notes = st.text_input("审核备注", key="review_notes")
    approve_column, reject_column = st.columns(2)
    if approve_column.button("批准", type="primary"):
        final = get_workflow().invoke(
            Command(resume={"approved": True, "notes": notes}), config
        )
        st.session_state.result = final
        st.rerun()
    if reject_column.button("退回修改"):
        final = get_workflow().invoke(
            Command(resume={"approved": False, "notes": notes}), config
        )
        st.session_state.result = final
        st.rerun()


def _render_qa() -> None:
    st.divider()
    st.subheader("基于官网证据提问")
    question = st.text_input(
        "问题（中文、英文或越南语）",
        placeholder="南京大学长期汉语一学年学费是多少？",
    )
    if not st.button("回答", disabled=not question.strip()):
        return
    try:
        with st.spinner("检索并生成引用回答…"):
            hits = get_retriever()(question)
            answer = answer_question(
                load_deepseek_chat_model(max_tokens=900),
                question,
                hits,
            )
    except MissingAPIKeyError:
        st.error("未配置 DEEPSEEK_API_KEY，无法生成回答。")
        return
    except FileNotFoundError:
        st.error("未找到本地 Chroma 索引，请先按 docs/local-embeddings.md 构建。")
        return
    except GroundedAnswerError as error:
        st.error(f"回答未通过引用校验：{error}")
        return
    except Exception as error:  # noqa: BLE001 - surface upstream failures in the demo
        st.error(f"回答失败：{error}")
        return

    if answer.insufficient_evidence:
        st.warning(answer.answer)
    else:
        st.markdown(answer.answer)
    if answer.citations:
        titles = get_source_titles()
        st.write("**引用**")
        for citation in answer.citations:
            title = titles.get(citation.source_id, citation.source_id)
            st.markdown(
                f"- [{title}]({citation.source_url}) · {citation.admission_cycle}"
                f" · 采集 {citation.accessed_at}"
            )
            st.caption(f"> {citation.quote}")


def main() -> None:
    st.title("南京高校一年制汉语项目售前工作台")
    st.caption("结构化学生背景 → 官网证据推荐表 → 人工确认 → 引用问答")

    pack = get_city_pack()
    active = sum(1 for university in pack.universities if university.pool_status == "active")
    pending = sum(1 for university in pack.universities if university.pool_status == "pending")

    with st.sidebar:
        st.header("工作台状态")
        st.write(f"城市：{pack.city}")
        st.write(f"招生季：{pack.admission_cycle}")
        st.write(f"学校：{active} 所 active，{pending} 所 pending")
        st.write("DeepSeek：" + ("已配置" if os.environ.get("DEEPSEEK_API_KEY") else "未配置"))
        st.caption("推荐表只用于售前沟通，不是录取结论。")
        if st.button("新会话"):
            st.session_state.clear()
            st.rerun()

    with st.form("intake_form"):
        st.subheader("学生背景")
        first, second, third = st.columns(3)
        education_level = first.selectbox(
            "当前学历",
            ["high_school", "bachelor", "master", "other"],
            format_func=lambda value: {
                "high_school": "高中",
                "bachelor": "本科",
                "master": "硕士",
                "other": "其他",
            }[value],
        )
        graduation_status = second.selectbox(
            "毕业状态",
            ["expected_graduation", "graduated", "in_progress"],
            format_func=lambda value: {
                "expected_graduation": "预计毕业",
                "graduated": "已毕业",
                "in_progress": "在读",
            }[value],
        )
        native_language = third.text_input("母语", value="Vietnamese")

        fourth, fifth, sixth = st.columns(3)
        chinese_level = fourth.selectbox(
            "中文水平",
            ["none", "beginner", "intermediate", "advanced"],
            index=1,
            format_func=lambda value: {
                "none": "零基础",
                "beginner": "初级",
                "intermediate": "中级",
                "advanced": "高级",
            }[value],
        )
        hsk_level = fifth.slider("HSK 等级", 1, 6, 4)
        hsk_score = sixth.number_input("HSK 分数", min_value=0, max_value=300, value=210)

        seventh, eighth, ninth = st.columns(3)
        ielts_score = seventh.number_input(
            "雅思（可选，0 表示没有）", min_value=0.0, max_value=9.0, value=6.0, step=0.5
        )
        annual_budget = eighth.number_input(
            "年度预算（人民币）", min_value=0, max_value=200_000, value=30_000, step=1_000
        )
        needs_dormitory = ninth.checkbox("需要宿舍", value=True)

        preferred_tiers = st.multiselect(
            "偏好档次",
            ["reach", "match", "safety"],
            default=["reach", "match", "safety"],
            format_func=lambda value: {
                "reach": "冲刺档",
                "match": "匹配档",
                "safety": "保底档",
            }[value],
        )
        submitted = st.form_submit_button("生成推荐表", type="primary")

    if submitted:
        payload = build_intake(
            intake_id=uuid.uuid4().hex,
            education_level=education_level,
            graduation_status=graduation_status,
            native_language=native_language,
            chinese_level=chinese_level,
            hsk_level=hsk_level,
            hsk_score=int(hsk_score),
            ielts_score=ielts_score or None,
            annual_budget_cny=float(annual_budget),
            needs_dormitory=needs_dormitory,
            preferred_tiers=preferred_tiers,
        )
        st.session_state.thread_id = uuid.uuid4().hex
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        try:
            with st.spinner("检索并生成推荐表…"):
                st.session_state.result = get_workflow().invoke({"intake": payload}, config)
        except Exception as error:  # noqa: BLE001 - surface setup errors in the demo
            st.error(f"生成失败：{error}")

    result = st.session_state.get("result")
    if result:
        report = result.get("report")
        if report:
            _render_report(report)
        config = {"configurable": {"thread_id": st.session_state.get("thread_id")}}
        _render_review(result, config)

    _render_qa()


main()
