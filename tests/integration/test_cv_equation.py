"""Integration tests for cv-headings-lists-equation-footer.hwpx."""

import json
import pathlib

import pytest

from openhanji.document import ImageRef, Paragraph, ParagraphStyle

import openhanji

FIXTURE = (
    pathlib.Path(__file__).parent.parent
    / "test_files" / "hwpx" / "lab_cv-headings-lists-equation-footer.hwpx"
)


@pytest.fixture(scope="module")
def doc():
    return openhanji.open(FIXTURE)


class DescribeStructure:

    def it_parses_without_error(self, doc):
        from openhanji.document import Document
        assert isinstance(doc, Document)

    def it_has_20_paragraphs(self, doc):
        assert len(doc.paragraphs) == 20

    def it_has_2_tables(self, doc):
        assert len(doc.tables) == 2

    def it_has_22_blocks(self, doc):
        assert len(doc.blocks) == 22

    def it_has_no_top_level_images(self, doc):
        assert len(doc.images) == 0

    def it_has_one_section(self, doc):
        assert len(doc.sections) == 1

    def it_block_indices_are_sequential(self, doc):
        assert [b.index for b in doc.blocks] == list(range(len(doc.blocks)))

    def it_has_no_headers(self, doc):
        assert len(doc.headers) == 0


class DescribeMetadata:

    def it_has_keywords(self, doc):
        assert doc.metadata.keywords

    def it_keywords_contain_sxa_lab(self, doc):
        joined = " ".join(doc.metadata.keywords)
        assert "SxA Lab" in joined

    def it_has_created_at(self, doc):
        assert doc.metadata.created_at is not None

    def it_has_modified_at(self, doc):
        assert doc.metadata.modified_at is not None

    def it_has_title(self, doc):
        assert doc.metadata.title == "This is A metadat test"

    def it_has_author(self, doc):
        assert doc.metadata.author == "SxA 랩"

    def it_has_subject(self, doc):
        assert doc.metadata.subject == "metadata test"


class DescribeFooter:
    """Footer contains a Paragraph, an ImageRef, and a Paragraph with a link."""

    def it_has_three_footer_blocks(self, doc):
        assert len(doc.footers) == 3

    def it_first_footer_block_is_paragraph(self, doc):
        assert isinstance(doc.footers[0], Paragraph)

    def it_second_footer_block_is_imageref(self, doc):
        assert isinstance(doc.footers[1], ImageRef)

    def it_third_footer_block_is_paragraph(self, doc):
        assert isinstance(doc.footers[2], Paragraph)

    def it_third_footer_paragraph_has_hyperlink(self, doc):
        para = doc.footers[2]
        assert isinstance(para, Paragraph)
        hrefs = [r.href for r in para.runs if r.href]
        assert hrefs

    def it_footer_link_points_to_sxa_lab(self, doc):
        para = doc.footers[2]
        assert isinstance(para, Paragraph)
        hrefs = [r.href for r in para.runs if r.href]
        assert any("sxa-lab" in h for h in hrefs)


class DescribeHeadings:

    def it_detects_headings(self, doc):
        headings = [p for p in doc.paragraphs if p.style != ParagraphStyle.BODY]
        assert headings

    def it_detects_heading1(self, doc):
        assert any(p.style == ParagraphStyle.HEADING1 for p in doc.paragraphs)

    def it_detects_heading2(self, doc):
        assert any(p.style == ParagraphStyle.HEADING2 for p in doc.paragraphs)


class DescribeEquation:

    def it_equation_renders_as_placeholder(self, doc):
        equation_paras = [p for p in doc.paragraphs if p.text == "[수식]"]
        assert equation_paras, "expected at least one equation placeholder paragraph"

    def it_equation_placeholder_is_body_style(self, doc):
        for p in doc.paragraphs:
            if p.text == "[수식]":
                assert p.style == ParagraphStyle.BODY


class DescribeRunTextInvariant:

    def it_holds_for_all_paragraphs(self, doc):
        for para in doc.paragraphs:
            if para.runs:
                assert para.text == "".join(r.text for r in para.runs)

    def it_holds_for_footer_paragraphs(self, doc):
        for block in doc.footers:
            if isinstance(block, Paragraph) and block.runs:
                assert block.text == "".join(r.text for r in block.runs)

    def it_holds_for_cell_paragraphs(self, doc):
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    for block in cell.blocks:
                        if isinstance(block, Paragraph) and block.runs:
                            assert block.text == "".join(r.text for r in block.runs)


class DescribeStrictMode:

    def it_parses_under_strict_true(self):
        doc = openhanji.open(FIXTURE, strict=True)
        assert len(doc.blocks) == 22

    def it_block_count_unchanged_in_strict_mode(self):
        assert len(openhanji.open(FIXTURE).blocks) == len(
            openhanji.open(FIXTURE, strict=True).blocks
        )


class DescribeOutputFormats:

    def it_to_json_body_length_matches_blocks(self, doc):
        data = json.loads(doc.to_json())
        assert len(data["body"]) == len(doc.blocks)

    def it_to_json_has_footers_key(self, doc):
        data = json.loads(doc.to_json())
        assert "footers" in data

    def it_to_json_structured_sections_sum_matches(self, doc):
        data = json.loads(doc.to_json(mode="structured"))
        total = sum(len(s["blocks"]) for s in data["sections"])
        assert total == len(doc.blocks)

    def it_to_markdown_is_non_empty(self, doc):
        assert doc.to_markdown().strip()

    def it_to_markdown_has_footer_comment(self, doc):
        assert "<!-- footer:" in doc.to_markdown()

    def it_to_markdown_has_hash_headings(self, doc):
        assert any(l.startswith("#") for l in doc.to_markdown().splitlines())

    def it_to_markdown_footer_contains_link_text(self, doc):
        # footer runs are flattened to plain text in markdown (no run-level formatting)
        assert "and a link here" in doc.to_markdown()

    def it_to_text_is_non_empty(self, doc):
        assert doc.to_text().strip()

    def it_to_json_block_types_are_valid(self, doc):
        data = json.loads(doc.to_json())
        bad = [b for b in data["body"] if b["type"] not in {"paragraph", "table", "image"}]
        assert not bad
