import json
from pathlib import Path

from study_abroad.catalog_validation import CatalogSource
from study_abroad.city_catalog import CityPack
from study_abroad.city_rag import chunks_from_catalog_sources, chunks_from_city_pack


def _pack() -> CityPack:
    payload = json.loads(
        Path("data/city_packs/nanjing_pack_v1.json").read_text(encoding="utf-8")
    )
    return CityPack(**payload)


def test_city_pack_produces_one_fact_chunk_per_active_program() -> None:
    chunks = chunks_from_city_pack(_pack())

    assert len(chunks) == 3
    assert len({chunk.chunk_id for chunk in chunks}) == 3
    assert all(chunk.source_quote for chunk in chunks)
    assert all(chunk.program_id for chunk in chunks)
    assert all(chunk.source_type == "program_fact" for chunk in chunks)


def test_city_chunks_include_fees_deadlines_and_review_flags() -> None:
    chunks = chunks_from_city_pack(_pack())
    by_program = {chunk.program_id: chunk for chunk in chunks}

    assert "Tuition: 21000 CNY per year" in by_program["nju_2027_one_year_chinese"].text
    assert (
        "Application deadline: 2027-07-30"
        in by_program["seu_2027_chinese_student_program"].text
    )
    assert (
        "Review flags: needs_manual_review:application_deadline"
        in by_program["njnu_2027_one_year_chinese_preparatory"].text
    )


def test_city_chunks_keep_source_trace() -> None:
    chunks = chunks_from_city_pack(_pack())
    by_program = {chunk.program_id: chunk for chunk in chunks}

    njnu = by_program["njnu_2027_one_year_chinese_preparatory"]
    assert njnu.document_id == "njnu_2027_international_guide"
    assert njnu.source_url == "https://gjc.njnu.edu.cn/info/1035/7544.htm"
    assert "一年汉语" in njnu.source_quote


def test_catalog_source_text_produces_source_chunks() -> None:
    pack = _pack()
    source = CatalogSource(
        source_id="nju_hwxy_long_term_chinese",
        url="https://hwxy.nju.edu.cn/guide",
        text="南京大学长期汉语进修。" * 200,
        university="Nanjing University",
        title="长期汉语进修",
        accessed_at="2026-11-23",
    )

    chunks = chunks_from_catalog_sources(pack, {source.source_id: source})

    assert len(chunks) > 1
    assert all(chunk.document_id == source.source_id for chunk in chunks)
    assert all(chunk.university == "Nanjing University" for chunk in chunks)
    assert all(chunk.source_type == "web_snapshot" for chunk in chunks)
    assert all(chunk.source_quote for chunk in chunks)
