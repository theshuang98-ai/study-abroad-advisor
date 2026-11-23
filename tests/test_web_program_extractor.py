from study_abroad.web_program_extractor import extract_program_candidates

SOURCE = {
    "source_id": "xmu_2027_cn_bachelor_catalog",
    "university": "Xiamen University",
    "title": "2027 XMU Chinese-Medium Bachelor's Programs",
    "admission_cycle": "2027_entry",
    "url": "https://admissions.xmu.edu.cn/programs",
}


def _table(rows: str) -> str:
    return f"<html><body><div id='vsb_content'><table>{rows}</table></div></body></html>"


def test_rowspan_context_is_repeated_for_covered_rows() -> None:
    html = _table(
        """
        <tr>
          <th>No.</th><th>Location</th><th>Departments</th>
          <th>Programs/Majors</th><th>Medium of Instructions</th><th>Duration</th>
        </tr>
        <tr>
          <td>1</td><td rowspan="2">Siming Campus</td>
          <td rowspan="2">Dept. of Finance</td><td>Finance</td>
          <td rowspan="2">Chinese</td><td rowspan="2">4</td>
        </tr>
        <tr><td>2</td><td>Accounting</td></tr>
        """
    )

    result = extract_program_candidates(html, SOURCE)

    assert result.warnings == ()
    assert [candidate.program_name for candidate in result.candidates] == [
        "Finance",
        "Accounting",
    ]
    assert [candidate.candidate_id for candidate in result.candidates] == [
        "xmu_2027_cn_bachelor_catalog#r1",
        "xmu_2027_cn_bachelor_catalog#r2",
    ]
    second = result.candidates[1].text
    assert "Location: Siming Campus" in second
    assert "Departments: Dept. of Finance" in second
    assert "Medium of Instructions: Chinese" in second
    assert "Duration: 4" in second
    assert "Programs/Majors: Accounting" in second


def test_table_without_program_header_is_not_mapped_by_position() -> None:
    html = _table(
        """
        <tr><th>No.</th><th>Programs</th></tr>
        <tr><td>1</td><td>Undergraduate</td></tr>
        """
    )

    result = extract_program_candidates(html, SOURCE)

    assert result.candidates == ()
    assert "no Programs/Majors header" in result.warnings[0]


def test_page_without_tables_returns_warning() -> None:
    result = extract_program_candidates("<html><body><p>Admission rules.</p></body></html>", SOURCE)

    assert result.candidates == ()
    assert result.warnings == ("no tables found",)


def test_rows_without_program_name_are_skipped_and_reported() -> None:
    html = _table(
        """
        <tr><th>No.</th><th>Programs/Majors</th></tr>
        <tr><td>1</td><td>Finance</td></tr>
        <tr><td>2</td><td></td></tr>
        """
    )

    result = extract_program_candidates(html, SOURCE)

    assert [candidate.program_name for candidate in result.candidates] == ["Finance"]
    assert "row 2: missing program name" in result.warnings[0]
