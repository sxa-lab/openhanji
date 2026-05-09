"""Integration tests for marketing-plan.hwpx."""

import pathlib
import re

import pytest

import openhanji
from openhanji.models.document import ParagraphStyle
from tests.integration.builders import (
    assert_block_indices_sequential,
    assert_none_mode_block_count_unchanged,
    assert_none_mode_no_headings,
    assert_run_text_invariant,
    assert_run_text_invariant_cells,
    assert_strict_block_count_unchanged,
    assert_to_json_body_matches_blocks,
    assert_to_json_structured_sections_match,
    assert_to_markdown_non_empty,
    assert_to_text_non_empty,
)

FIXTURE = (
    pathlib.Path(__file__).parent.parent
    / "test_files"
    / "hwpx"
    / "lab_marketing-plan.hwpx"
)
_KO = re.compile(r"[가-힣]")


@pytest.fixture(scope="module")
def doc():
    return openhanji.open(FIXTURE)


@pytest.fixture(scope="module")
def doc_with_images():
    return openhanji.open(FIXTURE, with_images=True)


class DescribeStructure:
    def it_parses_without_error(self, doc):
        from openhanji.models.document import Document

        assert isinstance(doc, Document)

    def it_has_48_paragraphs(self, doc):
        assert len(doc.paragraphs) == 48

    def it_has_4_tables(self, doc):
        assert len(doc.tables) == 4

    def it_has_53_blocks(self, doc):
        assert len(doc.blocks) == 53

    def it_has_one_image(self, doc):
        assert len(doc.images) == 1

    def it_block_indices_are_sequential(self, doc):
        assert_block_indices_sequential(doc)

    def it_has_no_headers(self, doc):
        assert len(doc.headers) == 0

    def it_has_no_footers(self, doc):
        assert len(doc.footers) == 0


class DescribeHeadings:
    def it_detects_25_non_body_paragraphs(self, doc):
        non_body = [p for p in doc.paragraphs if p.style != ParagraphStyle.BODY]
        assert len(non_body) == 25

    def it_detects_23_headings(self, doc):
        headings = [p for p in doc.paragraphs if p.style.value.startswith("HEADING")]
        assert len(headings) == 23

    def it_detects_2_list_paragraphs(self, doc):
        lists = [
            p
            for p in doc.paragraphs
            if p.style in (ParagraphStyle.LIST_ORDERED, ParagraphStyle.LIST_UNORDERED)
        ]
        assert len(lists) == 2

    def it_detects_heading1_and_heading2(self, doc):
        styles = {p.style for p in doc.paragraphs if p.style != ParagraphStyle.BODY}
        assert ParagraphStyle.HEADING1 in styles
        assert ParagraphStyle.HEADING2 in styles

    def it_has_korean_text(self, doc):
        all_text = " ".join(p.text for p in doc.paragraphs)
        assert _KO.search(all_text)


class DescribeRunTextInvariant:
    def it_holds_for_all_paragraphs(self, doc):
        assert_run_text_invariant(doc)

    def it_holds_for_all_cell_paragraphs(self, doc):
        assert_run_text_invariant_cells(doc)


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
    def it_to_json_body_length_matches_blocks(self, doc):
        assert_to_json_body_matches_blocks(doc)

    def it_to_json_structured_sections_sum_matches(self, doc):
        assert_to_json_structured_sections_match(doc)

    def it_to_markdown_is_non_empty(self, doc):
        assert_to_markdown_non_empty(doc)

    def it_to_markdown_has_hash_headings(self, doc):
        assert any(line.startswith("#") for line in doc.to_markdown().splitlines())

    def it_to_text_is_non_empty(self, doc):
        assert_to_text_non_empty(doc)


class DescribeStrictMode:
    def it_parses_under_strict_true(self):
        doc = openhanji.open(FIXTURE, strict=True)
        assert len(doc.blocks) == 53

    def it_block_count_unchanged_in_strict_mode(self):
        assert_strict_block_count_unchanged(FIXTURE)


class DescribeHeadingDetection:
    def it_none_mode_produces_no_headings(self):
        assert_none_mode_no_headings(FIXTURE)

    def it_none_mode_block_count_unchanged(self):
        assert_none_mode_block_count_unchanged(FIXTURE)

    def it_structural_mode_headings_leq_auto(self):
        auto = sum(
            1
            for p in openhanji.open(FIXTURE).paragraphs
            if p.style != ParagraphStyle.BODY
        )
        struct = sum(
            1
            for p in openhanji.open(FIXTURE, heading_detection="structural").paragraphs
            if p.style != ParagraphStyle.BODY
        )
        assert struct <= auto
