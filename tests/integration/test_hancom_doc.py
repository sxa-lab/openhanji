"""Regression tests against fax-hancom.hwpx (Hancom Office-produced document)."""

import json
import pathlib

import pytest

import openhanji
from openhanji.document import Paragraph, Table

FIXTURE = (
    pathlib.Path(__file__).parent.parent / "test_files" / "hwpx" / "lab_fax-hancom.hwpx"
)


@pytest.fixture(scope="module")
def doc():
    return openhanji.open(FIXTURE)


class DescribeStructure:

    def it_parses_without_error(self, doc):
        from openhanji.document import Document
        assert isinstance(doc, Document)

    def it_has_four_tables(self, doc):
        assert len(doc.tables) == 4

    def it_has_no_top_level_paragraphs(self, doc):
        assert len(doc.paragraphs) == 0

    def it_has_four_blocks(self, doc):
        assert len(doc.blocks) == 4

    def it_has_no_images(self, doc):
        assert len(doc.images) == 0

    def it_block_indices_are_sequential(self, doc):
        indices = [b.index for b in doc.blocks]
        assert indices == list(range(len(indices)))


class DescribeHeaderFooter:

    def it_extracts_one_header(self, doc):
        assert len(doc.headers) == 1

    def it_extracts_one_footer(self, doc):
        assert len(doc.footers) == 1

    def it_header_is_paragraph(self, doc):
        assert isinstance(doc.headers[0], Paragraph)

    def it_footer_is_paragraph(self, doc):
        assert isinstance(doc.footers[0], Paragraph)

    def it_header_text_contains_sxa_lab(self, doc):
        assert "SxA Lab" in doc.headers[0].text

    def it_footer_text_contains_sxa_lab(self, doc):
        assert "SxA Lab" in doc.footers[0].text


class DescribeCellContent:

    def it_cell_text_accessible_for_all_cells(self, doc):
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    _ = cell.text

    def it_first_table_has_one_row(self, doc):
        assert len(doc.tables[0].rows) == 1

    def it_second_table_has_four_rows(self, doc):
        assert len(doc.tables[1].rows) == 4

    def it_run_text_invariant_holds(self, doc):
        for tbl in doc.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    for block in cell.blocks:
                        if isinstance(block, Paragraph):
                            assert block.text == "".join(r.text for r in block.runs)


class DescribeStrictMode:

    def it_parses_under_strict_true(self):
        doc = openhanji.open(FIXTURE, strict=True)
        assert len(doc.blocks) == 4

    def it_strict_mode_does_not_change_block_count(self):
        assert len(openhanji.open(FIXTURE).blocks) == len(
            openhanji.open(FIXTURE, strict=True).blocks
        )


class DescribeOutputFormats:

    def it_to_json_is_valid(self, doc):
        data = json.loads(doc.to_json())
        assert "body" in data
        assert len(data["body"]) == len(doc.blocks)

    def it_to_json_structured_has_sections(self, doc):
        data = json.loads(doc.to_json(mode="structured"))
        assert "sections" in data

    def it_to_markdown_produces_string(self, doc):
        assert isinstance(doc.to_markdown(), str)

    def it_to_text_produces_string(self, doc):
        assert isinstance(doc.to_text(), str)

    def it_headers_appear_as_comments_in_markdown(self, doc):
        assert "<!-- header:" in doc.to_markdown()

    def it_footers_appear_as_comments_in_markdown(self, doc):
        assert "<!-- footer:" in doc.to_markdown()
