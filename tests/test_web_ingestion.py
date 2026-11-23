import pytest

from study_abroad.web_ingestion import SourceMeta, parse_html


def _meta(**overrides: str) -> SourceMeta:
    values = {
        "source_id": "zju_2027_undergraduate_guide",
        "university": "Zhejiang University",
        "title": "Application Guide for Undergraduate Programs 2027",
        "url": "https://example.edu/guide",
        "language": "en",
        "admission_cycle": "2027_entry",
        "accessed_at": "2026-11-19",
    }
    values.update(overrides)
    return SourceMeta(**values)


def _page(content: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><title>Page title</title><style>.x {{ color: red; }}</style></head>
<body>
<nav>Home Admissions Programs</nav>
<footer>Contact the admissions office</footer>
{content}
</body></html>"""


def test_parse_keeps_metadata_and_heading_hierarchy() -> None:
    html = _page(
        """
        <div class="wp_articlecontent">
          <h1>Application Guide</h1>
          <p>Zhejiang University admits international students twice a year.</p>
          <h2>Application Requirements</h2>
          <ul><li>High school diploma</li><li>Language certificate</li></ul>
        </div>
        """
    )

    doc = parse_html(html, _meta())

    assert doc.source_id == "zju_2027_undergraduate_guide"
    assert doc.document_id == doc.source_id
    assert doc.title == "Application Guide for Undergraduate Programs 2027"
    assert doc.url == "https://example.edu/guide"
    assert doc.admission_cycle == "2027_entry"
    assert doc.language == "en"
    assert doc.accessed_at == "2026-11-19"
    assert [section.heading for section in doc.sections] == [
        "Application Guide",
        "Application Requirements",
    ]
    assert [section.level for section in doc.sections] == [1, 2]
    assert [section.section_id for section in doc.sections] == [
        "zju_2027_undergraduate_guide#s0",
        "zju_2027_undergraduate_guide#s1",
    ]
    assert "High school diploma" in doc.sections[1].text
    assert "Home Admissions" not in doc.text
    assert "Contact the admissions office" not in doc.text
    assert "color: red" not in doc.text


def test_parse_table_rows_without_duplicating_cell_paragraphs() -> None:
    html = _page(
        """
        <div class="main">
          <div id="vsb_content">
            <p>Xiamen University Chinese-medium bachelor programs are listed below.</p>
            <table>
              <tr><th>Major</th><th>Duration</th></tr>
              <tr><td><p>Software Engineering</p></td><td>4 years</td></tr>
            </table>
          </div>
        </div>
        """
    )

    doc = parse_html(html, _meta(source_id="xmu_2027_cn_bachelor_catalog"))

    assert len(doc.sections) == 1
    assert doc.sections[0].heading is None
    assert "Software Engineering | 4 years" in doc.text
    assert doc.text.count("Software Engineering") == 1
    assert doc.text.count("4 years") == 1
    assert "Home Admissions" not in doc.text


def test_parse_numbered_paragraph_headings_and_join_split_spans() -> None:
    html = _page(
        """
        <div class="wp_articlecontent">
          <p>Programs for 202<span>7</span> in
             <span>research-</span><span>oriented</span> fields.</p>
          <p>I. Eligibility</p>
          <p>1. General Requirements</p>
          <p>1.1 Language Requirements</p>
          <p>Applicants must meet the language requirements.</p>
        </div>
        """
    )

    doc = parse_html(html, _meta())

    assert "Programs for 2027 in research-oriented fields." in doc.sections[0].text
    assert [(section.heading, section.level) for section in doc.sections[1:]] == [
        ("I. Eligibility", 2),
        ("1. General Requirements", 3),
        ("1.1 Language Requirements", 4),
    ]


def test_parse_raises_when_no_visible_text() -> None:
    html = "<html><body><nav>Only navigation</nav><script>var x = 1;</script></body></html>"

    with pytest.raises(ValueError, match="No extractable text"):
        parse_html(html, _meta())
