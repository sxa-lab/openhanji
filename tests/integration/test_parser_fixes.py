"""Regression tests for parser fixes:
- para.text preserves leading/trailing whitespace from runs
- _has_text recurses into nested cell blocks
- heading inference from font size + face heuristics
"""

import pathlib

import pytest

import openhanji
from openhanji.models.document import (
    Cell,
    Document,
    Paragraph,
    ParagraphStyle,
    Row,
    Table,
)

from tests.integration.builders import make_charpr_hwpx

TEST_FILES = pathlib.Path(__file__).parent.parent / "test_files"
FONT_FIXTURE = TEST_FILES / "hwpx" / "sxa_font-heading-heuristics.hwpx"
BASIC = TEST_FILES / "hwpx" / "sxa_owpml-structure-coverage.hwpx"


class DescribeParaTextWhitespace:
    def it_preserves_leading_whitespace(self):
        doc = openhanji.open(FONT_FIXTURE)
        # " 앞에 공백이 있는 단락" has one leading space
        para = next(p for p in doc.paragraphs if "앞에 공백" in p.text)
        assert para.text.startswith(" ")

    def it_preserves_double_indent(self):
        doc = openhanji.open(FONT_FIXTURE)
        para = next(p for p in doc.paragraphs if "두 칸 들여쓰기" in p.text)
        assert para.text.startswith("  ")

    def it_matches_run_join(self):
        doc = openhanji.open(FONT_FIXTURE)
        for para in doc.paragraphs:
            joined = "".join(r.text for r in para.runs)
            assert para.text == joined, (
                f"para.text={para.text!r} != run join={joined!r}"
            )

    def it_does_not_strip_trailing_whitespace(self):
        doc = openhanji.open(BASIC)
        # this document has no trailing-space runs, but para.text must match run join
        for para in doc.paragraphs:
            joined = "".join(r.text for r in para.runs)
            assert para.text == joined


class DescribeHeadingInference:
    def it_infers_h1_from_large_heading_font(self):
        doc = openhanji.open(FONT_FIXTURE)
        h1 = [p for p in doc.paragraphs if p.style == ParagraphStyle.HEADING1]
        assert len(h1) == 1
        assert "대분류 제목" in h1[0].text

    def it_infers_h2_from_medium_heading_font(self):
        doc = openhanji.open(FONT_FIXTURE)
        h2 = [p for p in doc.paragraphs if p.style == ParagraphStyle.HEADING2]
        assert len(h2) == 1
        assert "중분류 제목" in h2[0].text

    def it_does_not_promote_body_font_paragraphs(self):
        doc = openhanji.open(FONT_FIXTURE)
        body = [p for p in doc.paragraphs if p.style == ParagraphStyle.BODY]
        assert len(body) == 3  # the three 맑은 고딕 paragraphs

    def it_preserves_structural_outline_headings_unchanged(self):
        doc = openhanji.open(BASIC)
        h1 = [p for p in doc.paragraphs if p.style == ParagraphStyle.HEADING1]
        assert len(h1) > 0  # this document has outlineLevel headings

    def it_emits_hash_prefixes_in_markdown(self):
        doc = openhanji.open(FONT_FIXTURE)
        md = doc.to_markdown()
        assert "# 1. 대분류 제목" in md
        assert "## 1.1 중분류 제목" in md


class DescribeHasTextRecursion:
    def it_does_not_warn_for_nested_table_only_document(self, caplog):
        import logging

        # Build a document whose only text is inside a nested table
        inner_cell = Cell(blocks=[Paragraph(text="내부 텍스트", index=0)])
        inner_table = Table(rows=[Row(cells=[inner_cell])], index=0)
        outer_cell = Cell(blocks=[inner_table])
        outer_table = Table(rows=[Row(cells=[outer_cell])], index=0)
        doc = Document(body=[outer_table])

        with caplog.at_level(logging.WARNING, logger="openhanji"):
            # Simulate what _parse_body does after walking
            from openhanji.parsers.hwpx import HwpxParser

            parser = HwpxParser()
            has_text = parser._has_text(doc.blocks)

        assert has_text is True

    def it_returns_false_for_truly_empty_document(self):
        from openhanji.parsers.hwpx import HwpxParser

        empty_cell = Cell(blocks=[])
        table = Table(rows=[Row(cells=[empty_cell])], index=0)
        doc = Document(body=[table])
        assert HwpxParser()._has_text(doc.blocks) is False

    def it_finds_text_in_paragraph_blocks_directly(self):
        from openhanji.parsers.hwpx import HwpxParser

        doc = Document(body=[Paragraph(text="hello", index=0)])
        assert HwpxParser()._has_text(doc.blocks) is True


# ---------------------------------------------------------------------------
# Parametrized heuristic coverage — inline XML, no document file
# ---------------------------------------------------------------------------




class DescribeHeadingHeuristic:
    """Parametrized coverage of _infer_heading_from_runs.

    Each case is: (font_face, size_pt, bold, text, expected_style).
    Hancom default body is 10-11pt.  Heading sizes are 16pt (H2) and 18pt+ (H1).
    The size-only branch requires bold as a co-signal to avoid false positives
    on large-body-text templates.
    """

    @pytest.mark.parametrize(
        ("font_face", "size_pt", "bold", "text", "expected"),
        [
            # heading font face — size drives level, bold not required
            # H1 threshold: >= 15pt (primary section headers in real docs use 15pt)
            ("HY헤드라인M", 20, False, "제목", ParagraphStyle.HEADING1),
            ("HY헤드라인M", 18, False, "제목", ParagraphStyle.HEADING1),
            ("HY헤드라인M", 16, False, "제목", ParagraphStyle.HEADING1),
            ("HY헤드라인M", 15, False, "제목", ParagraphStyle.HEADING1),
            # H2 threshold: 12–13pt subsection headers
            ("HY헤드라인M", 13, False, "소제목", ParagraphStyle.HEADING2),
            ("HY헤드라인M", 12, False, "소소제목", ParagraphStyle.HEADING2),
            ("HY헤드라인M", 10, False, "본문 주석", ParagraphStyle.BODY),
            # 맑은 고딕 is a body font — never promoted regardless of size or bold
            ("맑은 고딕", 18, True, "굵은 제목", ParagraphStyle.BODY),
            ("맑은 고딕", 16, True, "굵은 부제목", ParagraphStyle.BODY),
            ("맑은 고딕", 18, False, "큰 본문", ParagraphStyle.BODY),
            ("맑은 고딕", 16, False, "큰 본문", ParagraphStyle.BODY),
            # body sizes — never heading regardless of bold or face
            ("HY헤드라인M", 11, True, "작은 주석", ParagraphStyle.BODY),
            ("맑은 고딕", 10, True, "기본 본문", ParagraphStyle.BODY),
            # paragraph over 120 chars — heuristic must not fire
            ("HY헤드라인M", 18, False, "가" * 121, ParagraphStyle.BODY),
            ("맑은 고딕", 18, True, "나" * 121, ParagraphStyle.BODY),
        ],
    )
    def it_classifies_correctly(
        self,
        tmp_path: pathlib.Path,
        font_face: str,
        size_pt: float,
        bold: bool,
        text: str,
        expected: ParagraphStyle,
    ) -> None:
        path = make_charpr_hwpx(
            tmp_path,
            font_face=font_face,
            font_size_hwpunit=int(size_pt * 100),
            bold=bold,
            text=text,
        )
        doc = openhanji.open(path)
        assert len(doc.paragraphs) == 1
        assert doc.paragraphs[0].style == expected, (
            f"font={font_face!r} size={size_pt}pt bold={bold} "
            f"text={text[:20]!r} → got {doc.paragraphs[0].style}, want {expected}"
        )
