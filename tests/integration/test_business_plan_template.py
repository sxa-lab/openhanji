"""Integration tests for business-plan-template.hwpx."""

import json
import pathlib

import pytest

from openhanji.document import ParagraphStyle

import openhanji

FIXTURE = (
    pathlib.Path(__file__).parent.parent
    / "test_files" / "hwpx" / "lab_business-plan-template.hwpx"
)


@pytest.fixture(scope="module")
def doc():
    return openhanji.open(FIXTURE)


@pytest.fixture(scope="module")
def doc_with_images():
    return openhanji.open(FIXTURE, with_images=True)


class DescribeStructure:

    def it_parses_without_error(self, doc):
        from openhanji.document import Document
        assert isinstance(doc, Document)

    def it_has_41_paragraphs(self, doc):
        assert len(doc.paragraphs) == 41

    def it_has_61_tables(self, doc):
        assert len(doc.tables) == 61

    def it_has_103_blocks(self, doc):
        assert len(doc.blocks) == 103

    def it_has_one_image(self, doc):
        assert len(doc.images) == 1

    def it_block_indices_are_sequential(self, doc):
        assert [b.index for b in doc.blocks] == list(range(len(doc.blocks)))

    def it_has_header(self, doc):
        assert len(doc.headers) == 1

    def it_has_footer(self, doc):
        assert len(doc.footers) == 1


class DescribeHeadings:

    def it_detects_34_headings(self, doc):
        headings = [p for p in doc.paragraphs if p.style != ParagraphStyle.BODY]
        assert len(headings) == 34

    def it_detects_heading1_and_heading2(self, doc):
        styles = {p.style for p in doc.paragraphs if p.style != ParagraphStyle.BODY}
        assert ParagraphStyle.HEADING1 in styles
        assert ParagraphStyle.HEADING2 in styles

    def it_has_korean_text(self, doc):
        import re
        ko = re.compile(r"[가-힣]")
        all_text = " ".join(p.text for p in doc.paragraphs)
        assert ko.search(all_text)


class DescribeRunTextInvariant:

    def it_holds_for_all_paragraphs(self, doc):
        for para in doc.paragraphs:
            if para.runs:
                assert para.text == "".join(r.text for r in para.runs)

    def it_holds_for_all_cell_paragraphs(self, doc):
        from openhanji.document import Paragraph
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    for block in cell.blocks:
                        if isinstance(block, Paragraph) and block.runs:
                            assert block.text == "".join(r.text for r in block.runs)


class DescribeImages:

    def it_default_image_has_no_data(self, doc):
        assert all(img.data is None for img in doc.images)

    def it_with_images_loads_binary(self, doc_with_images):
        assert any(img.data is not None for img in doc_with_images.images)

    def it_with_images_data_is_bytes(self, doc_with_images):
        for img in doc_with_images.images:
            if img.data is not None:
                assert isinstance(img.data, bytes)

    def it_with_images_emits_data_uri_in_markdown(self, doc_with_images):
        md = doc_with_images.to_markdown()
        assert "data:" in md and "base64," in md


class DescribeOutputFormats:

    def it_to_json_flat_body_length_matches_blocks(self, doc):
        data = json.loads(doc.to_json())
        assert len(data["body"]) == len(doc.blocks)

    def it_to_json_structured_sections_blocks_sum_matches(self, doc):
        data = json.loads(doc.to_json(mode="structured"))
        total = sum(len(s["blocks"]) for s in data["sections"])
        assert total == len(doc.blocks)

    def it_to_markdown_is_non_empty(self, doc):
        assert doc.to_markdown().strip()

    def it_to_markdown_has_hash_headings(self, doc):
        assert any(l.startswith("#") for l in doc.to_markdown().splitlines())

    def it_to_text_is_non_empty(self, doc):
        assert doc.to_text().strip()


class DescribeStrictMode:

    def it_parses_under_strict_true(self):
        doc = openhanji.open(FIXTURE, strict=True)
        assert len(doc.blocks) == 103

    def it_block_count_unchanged_in_strict_mode(self):
        assert len(openhanji.open(FIXTURE).blocks) == len(
            openhanji.open(FIXTURE, strict=True).blocks
        )


class DescribeHeadingDetection:

    def it_none_mode_produces_no_headings(self):
        doc = openhanji.open(FIXTURE, heading_detection="none")
        assert all(p.style == ParagraphStyle.BODY for p in doc.paragraphs)

    def it_none_mode_block_count_unchanged(self):
        assert len(openhanji.open(FIXTURE).blocks) == len(
            openhanji.open(FIXTURE, heading_detection="none").blocks
        )

    def it_structural_mode_headings_leq_auto(self):
        auto = sum(
            1 for p in openhanji.open(FIXTURE).paragraphs
            if p.style != ParagraphStyle.BODY
        )
        struct = sum(
            1 for p in openhanji.open(FIXTURE, heading_detection="structural").paragraphs
            if p.style != ParagraphStyle.BODY
        )
        assert struct <= auto
