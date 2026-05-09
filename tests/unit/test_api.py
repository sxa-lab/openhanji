"""validate the public API surface, excluding the files.

Run with: pytest tests/unit/test_api.py
"""

import json

import pytest

import openhanji
from openhanji.converters.json import to_json
from openhanji.exceptions import NotSupportedError
from openhanji.models.document import (
    Cell,
    Document,
    ImageRef,
    Metadata,
    Paragraph,
    ParagraphStyle,
    Row,
    Run,
    Section,
    Table,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _para(
    text: str,
    style: ParagraphStyle = ParagraphStyle.BODY,
    level: int = 0,
) -> Paragraph:
    return Paragraph(text=text, style=style, level=level, runs=[Run(text=text)])


def _heading(level: int, text: str) -> Paragraph:
    style = ParagraphStyle[f"HEADING{level}"]
    return Paragraph(text=text, style=style, runs=[Run(text=text)])


# errors
def test_open_hwp_raises_not_supported(tmp_path):
    fake = tmp_path / "test.hwp"
    fake.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(NotSupportedError):
        openhanji.open(fake)


def test_open_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        openhanji.open("/nonexistent/path/file.hwpx")


def test_open_unsupported_extension(tmp_path):
    f = tmp_path / "test.cell"
    f.write_bytes(b"")
    with pytest.raises(NotSupportedError):
        openhanji.open(f)


# document model
def _make_doc() -> Document:
    meta = Metadata(title="Test Doc", author="SxA Lab", keywords=["test", "hwpx"])

    def cell(text: str) -> Cell:
        return Cell(blocks=[Paragraph(text=text)])

    body = [
        Paragraph(text="Introduction", style=ParagraphStyle.HEADING1, index=0),
        Paragraph(
            text="Hello world",
            style=ParagraphStyle.BODY,
            runs=[Run(text="Hello "), Run(text="world")],
            index=1,
        ),
        Table(
            rows=[
                Row(cells=[cell("Name"), cell("Value")]),
                Row(cells=[cell("Alpha"), cell("1")]),
            ],
            index=2,
        ),
        ImageRef(index=3, caption="Figure 1"),
    ]
    return Document(metadata=meta, body=body)


def test_document_paragraphs():
    doc = _make_doc()
    assert len(doc.paragraphs) == 2
    assert doc.paragraphs[0].text == "Introduction"


def test_document_tables():
    doc = _make_doc()
    assert len(doc.tables) == 1
    assert doc.tables[0].rows[0].cells[0].text == "Name"


def test_document_images():
    doc = _make_doc()
    assert len(doc.images) == 1
    assert doc.images[0].caption == "Figure 1"


# json
def test_to_json_is_valid():
    doc = _make_doc()
    data = json.loads(to_json(doc))
    assert data["metadata"]["title"] == "Test Doc"
    assert data["metadata"]["keywords"] == ["test", "hwpx"]
    assert len(data["body"]) == 4
    assert data["body"][0]["type"] == "paragraph"
    assert data["body"][2]["type"] == "table"
    assert data["body"][3]["type"] == "image"


# markdown
def test_to_markdown_headings():
    doc = _make_doc()
    md = doc.to_markdown()
    assert "# Introduction" in md


def test_to_markdown_table():
    doc = _make_doc()
    md = doc.to_markdown()
    assert "| Name | Value |" in md
    assert "| ---" in md


def test_to_markdown_runs():
    doc = _make_doc()
    md = doc.to_markdown()
    assert "Hello" in md and "world" in md


# text
def test_to_text():
    doc = _make_doc()
    text = doc.to_text()
    assert "Introduction" in text
    assert "Hello world" in text
    assert "Name" in text


# repr
def test_repr():
    doc = _make_doc()
    r = repr(doc)
    assert "Test Doc" in r
    assert "paragraphs=2" in r


# LIST_ORDERED
def test_to_markdown_ordered_list():
    doc = Document(
        body=[
            Paragraph(
                text="First item",
                style=ParagraphStyle.LIST_ORDERED,
                level=0,
                index=0,
            ),
            Paragraph(
                text="Second item",
                style=ParagraphStyle.LIST_ORDERED,
                level=0,
                index=1,
            ),
            Paragraph(
                text="Nested item",
                style=ParagraphStyle.LIST_ORDERED,
                level=1,
                index=2,
            ),
        ]
    )
    md = doc.to_markdown()
    assert "1. First item" in md
    assert "1. Second item" in md
    assert "  1. Nested item" in md


def test_to_markdown_ordered_list_not_unordered():
    doc = Document(
        body=[
            Paragraph(text="Item", style=ParagraphStyle.LIST_ORDERED, level=0, index=0),
        ]
    )
    md = doc.to_markdown()
    assert "- Item" not in md
    assert "1. Item" in md


# page_count in JSON
def test_to_json_page_count():
    meta = Metadata(title="T", page_count=5)
    doc = Document(metadata=meta, body=[])
    data = json.loads(to_json(doc))
    assert data["metadata"]["page_count"] == 5


def test_to_json_page_count_none():
    meta = Metadata(title="T")
    doc = Document(metadata=meta, body=[])
    data = json.loads(to_json(doc))
    assert data["metadata"]["page_count"] is None


# ---------------------------------------------------------------------------
# Parametrized markdown output — specific line-level assertions
# ---------------------------------------------------------------------------


class DescribeMarkdownHeadings:
    @pytest.mark.parametrize(
        ("level", "text", "expected_line"),
        [
            (1, "제목 1", "# 제목 1"),
            (2, "제목 2", "## 제목 2"),
            (3, "제목 3", "### 제목 3"),
            (4, "제목 4", "#### 제목 4"),
            (5, "제목 5", "##### 제목 5"),
            (6, "제목 6", "###### 제목 6"),
        ],
    )
    def it_renders_each_heading_level(
        self, level: int, text: str, expected_line: str
    ) -> None:
        doc = Document(body=[_heading(level, text)])
        assert expected_line in doc.to_markdown().splitlines()

    def it_renders_body_without_hash_prefix(self) -> None:
        doc = Document(body=[_para("본문 텍스트")])
        lines = doc.to_markdown().splitlines()
        assert any(line == "본문 텍스트" for line in lines)
        assert not any(line.startswith("#") for line in lines)


class DescribeMarkdownRunFormatting:
    @pytest.mark.parametrize(
        ("bold", "italic", "expected_substr"),
        [
            (True, False, "**굵게**"),
            (False, True, "_기울임_"),
            (True, True, "***굵고 기울임***"),
        ],
    )
    def it_wraps_runs_with_correct_markers(
        self, bold: bool, italic: bool, expected_substr: str
    ) -> None:
        text = (
            "굵게"
            if bold and not italic
            else "기울임"
            if italic and not bold
            else "굵고 기울임"
        )
        doc = Document(
            body=[
                Paragraph(
                    text=text,
                    runs=[Run(text=text, bold=bold, italic=italic)],
                )
            ]
        )
        assert expected_substr in doc.to_markdown()

    def it_does_not_emit_underline_in_markdown(self) -> None:
        doc = Document(
            body=[Paragraph(text="밑줄", runs=[Run(text="밑줄", underline=True)])]
        )
        md = doc.to_markdown()
        assert "<u>" not in md
        assert "밑줄" in md


class DescribeMarkdownImagePlaceholders:
    def it_emits_unique_placeholder_names_for_multiple_images(self) -> None:
        doc = Document(
            body=[
                ImageRef(index=0, image_seq=0, caption="첫 번째"),
                ImageRef(index=1, image_seq=1, caption="두 번째"),
                ImageRef(index=2, image_seq=2),
            ]
        )
        md = doc.to_markdown()
        assert "![첫 번째](image_0)" in md
        assert "![두 번째](image_1)" in md
        assert "![image_2](image_2)" in md

    def it_uses_caption_as_alt_text_when_present(self) -> None:
        doc = Document(body=[ImageRef(index=0, image_seq=0, caption="Figure 1")])
        assert "![Figure 1]" in doc.to_markdown()

    def it_falls_back_to_image_seq_when_no_caption(self) -> None:
        doc = Document(body=[ImageRef(index=0, image_seq=3)])
        assert "![image_3](image_3)" in doc.to_markdown()


class DescribeMarkdownLists:
    @pytest.mark.parametrize(
        ("style", "level", "expected_prefix"),
        [
            (ParagraphStyle.LIST_UNORDERED, 0, "- "),
            (ParagraphStyle.LIST_UNORDERED, 1, "  - "),
            (ParagraphStyle.LIST_UNORDERED, 2, "    - "),
            (ParagraphStyle.LIST_ORDERED, 0, "1. "),
            (ParagraphStyle.LIST_ORDERED, 1, "  1. "),
            (ParagraphStyle.LIST_ORDERED, 2, "    1. "),
        ],
    )
    def it_renders_list_items_with_correct_indent(
        self, style: ParagraphStyle, level: int, expected_prefix: str
    ) -> None:
        doc = Document(body=[Paragraph(text="항목", style=style, level=level)])
        lines = doc.to_markdown().splitlines()
        assert any(line == expected_prefix + "항목" for line in lines)


class DescribeTextOutput:
    def it_flattens_table_cells_with_tabs(self) -> None:
        doc = Document(
            body=[
                Table(
                    rows=[
                        Row(
                            cells=[
                                Cell(
                                    blocks=[Paragraph(text="가", runs=[Run(text="가")])]
                                ),
                                Cell(
                                    blocks=[Paragraph(text="나", runs=[Run(text="나")])]
                                ),
                            ]
                        ),
                    ],
                    index=0,
                ),
            ]
        )
        text = doc.to_text()
        assert "가\t나" in text

    def it_omits_uncaptioned_images(self) -> None:
        doc = Document(body=[ImageRef(index=0, image_seq=0)])
        assert doc.to_text().strip() == ""

    def it_emits_caption_for_captioned_images(self) -> None:
        doc = Document(body=[ImageRef(index=0, image_seq=0, caption="도표 1")])
        assert "[Image: 도표 1]" in doc.to_text()


class DescribeJsonSerialization:
    @pytest.mark.parametrize(
        ("field", "value", "expected"),
        [
            ("bold", True, True),
            ("italic", True, True),
            ("underline", True, True),
            ("font_size", 14.0, 14.0),
            ("color", "#FF0000", "#FF0000"),
        ],
    )
    def it_includes_non_default_run_fields(
        self, field: str, value: object, expected: object
    ) -> None:
        run = Run(text="텍스트", **{field: value})  # type: ignore[arg-type]
        para = Paragraph(text="텍스트", runs=[run])
        doc = Document(body=[para])
        data = json.loads(to_json(doc))
        run_data = data["body"][0]["runs"][0]
        assert run_data[field] == expected

    def it_omits_default_run_fields(self) -> None:
        doc = Document(body=[Paragraph(text="기본", runs=[Run(text="기본")])])
        data = json.loads(to_json(doc))
        run_data = data["body"][0]["runs"][0]
        assert set(run_data.keys()) == {"text"}

    def it_serialises_image_data_as_null_when_absent(self) -> None:
        doc = Document(body=[ImageRef(index=0, image_seq=0)])
        data = json.loads(to_json(doc))
        assert data["body"][0]["data"] is None


class DescribeBoundaryDefaults:
    def it_run_with_no_args_serialises_to_text_only(self) -> None:
        run = Run(text="")
        doc = Document(body=[Paragraph(text="", runs=[run])])
        data = json.loads(to_json(doc))
        assert set(data["body"][0]["runs"][0].keys()) == {"text"}

    def it_empty_paragraph_to_text_returns_empty_string(self) -> None:
        doc = Document(body=[Paragraph(text="")])
        assert doc.to_text() == ""

    def it_empty_paragraph_to_markdown_returns_empty_string(self) -> None:
        doc = Document(body=[Paragraph(text="")])
        assert doc.to_markdown() == ""

    def it_document_with_no_body_has_empty_views(self) -> None:
        doc = Document()
        assert doc.paragraphs == []
        assert doc.tables == []
        assert doc.images == []

    def it_document_with_no_body_to_text_is_empty(self) -> None:
        assert Document().to_text() == ""

    def it_document_with_no_body_to_markdown_is_empty(self) -> None:
        assert Document().to_markdown() == ""

    def it_document_with_no_body_to_json_has_empty_body(self) -> None:
        data = json.loads(to_json(Document()))
        assert data["body"] == []


class DescribeSections:
    def it_constructs_from_sections_kwarg(self) -> None:
        sec = Section(
            blocks=[Paragraph(text="hello")],
            index=0,
            source_path="Contents/section0.xml",
        )
        doc = Document(sections=[sec])
        assert len(doc.sections) == 1
        assert doc.sections[0].source_path == "Contents/section0.xml"
        assert doc.sections[0].index == 0

    def it_body_convenience_produces_one_section(self) -> None:
        doc = Document(body=[Paragraph(text="hi"), Table()])
        assert len(doc.sections) == 1
        assert len(doc.sections[0].blocks) == 2

    def it_paragraphs_flattens_across_sections(self) -> None:
        s1 = Section(blocks=[Paragraph(text="first"), Paragraph(text="second")])
        s2 = Section(blocks=[Paragraph(text="third")])
        doc = Document(sections=[s1, s2])
        assert len(doc.paragraphs) == 3
        assert doc.paragraphs[2].text == "third"

    def it_tables_flattens_across_sections(self) -> None:
        s1 = Section(blocks=[Table(index=0)])
        s2 = Section(blocks=[Table(index=1)])
        doc = Document(sections=[s1, s2])
        assert len(doc.tables) == 2

    def it_images_flattens_across_sections(self) -> None:
        s1 = Section(blocks=[ImageRef(index=0, image_seq=0, caption="A")])
        s2 = Section(blocks=[ImageRef(index=1, image_seq=1, caption="B")])
        doc = Document(sections=[s1, s2])
        assert len(doc.images) == 2
        assert doc.images[1].caption == "B"

    def it_headers_and_footers_flatten_across_sections(self) -> None:
        s1 = Section(
            headers=[Paragraph(text="header1")],
            footers=[Paragraph(text="footer1")],
        )
        s2 = Section(
            headers=[Paragraph(text="header2")],
            footers=[Paragraph(text="footer2")],
        )
        doc = Document(sections=[s1, s2])
        assert len(doc.headers) == 2
        assert len(doc.footers) == 2
        assert doc.headers[0].text == "header1"
        assert doc.footers[1].text == "footer2"

    def it_section_filtered_views_do_not_cross_section_boundaries(self) -> None:
        sec = Section(
            blocks=[
                Paragraph(text="p1"),
                Table(index=0),
                ImageRef(index=0, image_seq=0),
            ]
        )
        assert len(sec.paragraphs) == 1
        assert len(sec.tables) == 1
        assert len(sec.images) == 1

    def it_json_output_keeps_flat_body_key(self) -> None:
        s1 = Section(blocks=[Paragraph(text="a")])
        s2 = Section(blocks=[Paragraph(text="b")])
        doc = Document(sections=[s1, s2])
        data = json.loads(to_json(doc))
        assert "body" in data
        assert len(data["body"]) == 2
        assert "sections" not in data

    def it_empty_sections_list_gives_empty_views(self) -> None:
        doc = Document(sections=[])
        assert doc.paragraphs == []
        assert doc.tables == []
        assert doc.images == []

    def it_repr_shows_section_count(self) -> None:
        doc = Document(sections=[Section(), Section()])
        assert "sections=2" in repr(doc)

    def it_headers_and_footers_accept_any_block_type(self) -> None:
        sec = Section(
            headers=[Paragraph(text="header para"), Table()],
            footers=[ImageRef(index=0, image_seq=0, caption="footer image")],
        )
        doc = Document(sections=[sec])
        assert len(doc.headers) == 2
        assert isinstance(doc.headers[0], Paragraph)
        assert isinstance(doc.headers[1], Table)
        assert isinstance(doc.footers[0], ImageRef)


class DescribeStructuredJson:
    def it_structured_mode_has_sections_key(self) -> None:
        s1 = Section(
            blocks=[Paragraph(text="a")],
            index=0,
            source_path="Contents/section0.xml",
        )
        s2 = Section(
            blocks=[Paragraph(text="b")],
            index=1,
            source_path="Contents/section1.xml",
        )
        doc = Document(sections=[s1, s2])
        data = json.loads(to_json(doc, mode="structured"))
        assert "sections" in data
        assert "body" not in data
        assert len(data["sections"]) == 2
        assert data["sections"][0]["source_path"] == "Contents/section0.xml"
        assert data["sections"][1]["index"] == 1

    def it_structured_mode_includes_blocks_per_section(self) -> None:
        sec = Section(blocks=[Paragraph(text="hello"), Table()])
        doc = Document(sections=[sec])
        data = json.loads(to_json(doc, mode="structured"))
        assert len(data["sections"][0]["blocks"]) == 2

    def it_flat_mode_is_default(self) -> None:
        doc = Document(body=[Paragraph(text="hi")])
        data = json.loads(to_json(doc))
        assert "body" in data
        assert "sections" not in data

    def it_structured_mode_section_has_headers_footers(self) -> None:
        sec = Section(
            blocks=[Paragraph(text="body")],
            headers=[Paragraph(text="head")],
            footers=[Paragraph(text="foot")],
        )
        doc = Document(sections=[sec])
        data = json.loads(to_json(doc, mode="structured"))
        assert data["sections"][0]["headers"][0]["text"] == "head"
        assert data["sections"][0]["footers"][0]["text"] == "foot"

    def it_source_path_is_null_when_not_set(self) -> None:
        sec = Section(blocks=[Paragraph(text="hi")])
        doc = Document(sections=[sec])
        data = json.loads(to_json(doc, mode="structured"))
        assert data["sections"][0]["source_path"] is None

    def it_flat_mode_preserves_headers_footers_at_top_level(self) -> None:
        sec = Section(
            blocks=[Paragraph(text="body")],
            headers=[Paragraph(text="head")],
            footers=[Paragraph(text="foot")],
        )
        doc = Document(sections=[sec])
        data = json.loads(to_json(doc, mode="flat"))
        assert data["headers"][0]["text"] == "head"
        assert data["footers"][0]["text"] == "foot"

    def it_section_uses_blocks_key_not_body(self) -> None:
        sec = Section(blocks=[Paragraph(text="x")])
        doc = Document(sections=[sec])
        data = json.loads(to_json(doc, mode="structured"))
        assert "blocks" in data["sections"][0]
        assert "body" not in data["sections"][0]

    def it_invalid_mode_raises_value_error(self) -> None:
        doc = Document()
        with pytest.raises(ValueError, match="mode"):
            to_json(doc, mode="bad")  # type: ignore[arg-type]


class DescribeNonParagraphHeaderFooter:
    def it_to_markdown_does_not_crash_with_table_in_header(self) -> None:
        sec = Section(
            blocks=[Paragraph(text="body")],
            headers=[Table(rows=[])],
        )
        doc = Document(sections=[sec])
        md = doc.to_markdown()
        assert "body" in md

    def it_to_text_does_not_crash_with_image_in_footer(self) -> None:
        sec = Section(
            blocks=[Paragraph(text="body")],
            footers=[ImageRef(index=0, image_seq=0, caption="fig")],
        )
        doc = Document(sections=[sec])
        text = doc.to_text()
        assert "body" in text

    def it_to_markdown_omits_table_from_header_comment(self) -> None:
        sec = Section(
            blocks=[Paragraph(text="body")],
            headers=[Paragraph(text="hdr"), Table(rows=[])],
        )
        doc = Document(sections=[sec])
        md = doc.to_markdown()
        assert "<!-- header: hdr -->" in md

    def it_structured_json_serialises_table_in_header(self) -> None:
        sec = Section(headers=[Table(rows=[])])
        doc = Document(sections=[sec])
        data = json.loads(to_json(doc, mode="structured"))
        assert data["sections"][0]["headers"][0]["type"] == "table"


class DescribeHeadingDetection:
    def it_auto_mode_infers_headings(self) -> None:
        doc = Document(
            body=[
                Paragraph(text="제목", style=ParagraphStyle.HEADING1),
                Paragraph(text="본문"),
            ]
        )
        md = doc.to_markdown()
        assert "# 제목" in md

    def it_none_mode_preserves_explicit_style_from_model(self) -> None:
        doc = Document(
            body=[
                Paragraph(text="제목", style=ParagraphStyle.HEADING1),
            ]
        )
        md = doc.to_markdown()
        assert "# 제목" in md


class DescribeHeadingDetectionValidation:
    def it_rejects_invalid_heading_detection_value(self, tmp_path) -> None:
        fake = tmp_path / "test.hwpx"
        fake.write_bytes(b"PK")  # won't be opened — validation fires first
        with pytest.raises(ValueError, match="heading_detection"):
            import openhanji

            openhanji.open(fake, heading_detection="bogus")
