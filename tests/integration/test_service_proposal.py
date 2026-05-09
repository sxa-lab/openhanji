"""Integration tests for service-proposal.hwpx."""

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
    assert_to_json_block_types_valid,
    assert_to_json_body_matches_blocks,
    assert_to_json_structured_sections_match,
    assert_to_markdown_non_empty,
    assert_to_text_non_empty,
)

FIXTURE = (
    pathlib.Path(__file__).parent.parent
    / "test_files"
    / "hwpx"
    / "lab_service-proposal.hwpx"
)
_KO = re.compile(r"[가-힣]")


@pytest.fixture(scope="module")
def doc():
    return openhanji.open(FIXTURE)


class DescribeStructure:
    def it_parses_without_error(self, doc):
        from openhanji.models.document import Document

        assert isinstance(doc, Document)

    def it_has_59_paragraphs(self, doc):
        assert len(doc.paragraphs) == 59

    def it_has_21_tables(self, doc):
        assert len(doc.tables) == 21

    def it_has_80_blocks(self, doc):
        assert len(doc.blocks) == 80

    def it_has_no_images(self, doc):
        assert len(doc.images) == 0

    def it_block_indices_are_sequential(self, doc):
        assert_block_indices_sequential(doc)

    def it_has_one_header(self, doc):
        assert len(doc.headers) == 1

    def it_has_no_footer(self, doc):
        assert len(doc.footers) == 0


class DescribeContent:
    def it_has_korean_text(self, doc):
        all_text = " ".join(p.text for p in doc.paragraphs)
        assert _KO.search(all_text)

    def it_has_no_heading_paragraphs(self, doc):
        assert not any(p.style.value.startswith("HEADING") for p in doc.paragraphs)

    def it_has_list_ordered_paragraphs(self, doc):
        lists = [p for p in doc.paragraphs if p.style == ParagraphStyle.LIST_ORDERED]
        assert len(lists) == 41

    def it_cell_text_accessible_for_all_cells(self, doc):
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    _ = cell.text


class DescribeRunTextInvariant:
    def it_holds_for_all_paragraphs(self, doc):
        assert_run_text_invariant(doc)

    def it_holds_for_all_cell_paragraphs(self, doc):
        assert_run_text_invariant_cells(doc)


class DescribeOutputFormats:
    def it_to_json_body_length_matches_blocks(self, doc):
        assert_to_json_body_matches_blocks(doc)

    def it_to_json_structured_sections_sum_matches(self, doc):
        assert_to_json_structured_sections_match(doc)

    def it_to_markdown_is_non_empty(self, doc):
        assert_to_markdown_non_empty(doc)

    def it_to_text_is_non_empty(self, doc):
        assert_to_text_non_empty(doc)

    def it_to_json_block_types_are_valid(self, doc):
        assert_to_json_block_types_valid(doc)


class DescribeStrictMode:
    def it_parses_under_strict_true(self):
        doc = openhanji.open(FIXTURE, strict=True)
        assert len(doc.blocks) == 80

    def it_block_count_unchanged_in_strict_mode(self):
        assert_strict_block_count_unchanged(FIXTURE)


class DescribeHeadingDetection:
    def it_none_mode_produces_no_headings(self):
        assert_none_mode_no_headings(FIXTURE)

    def it_none_mode_block_count_unchanged(self):
        assert_none_mode_block_count_unchanged(FIXTURE)
