"""Tests for structural list detection via HWPX numbering definitions.

Covers:
  - numbered list in top-level body → LIST_ORDERED
  - bullet list in top-level body → LIST_UNORDERED
  - list inside a table cell → correct style
  - numFormat mapping: DIGIT → ordered, DISC → unordered
  - missing numbering idRef → graceful fallback (no crash, BODY or ordered)
  - legacy autoNumFormat/bullet paraPr tags still work
  - block order and count unchanged after classification
  - heading_detection="none" suppresses headings but not lists
"""

from __future__ import annotations

import pathlib
import zipfile

import pytest

import openhanji
from openhanji.document import Paragraph, ParagraphStyle


# ---------------------------------------------------------------------------
# Minimal HWPX builder helpers
# ---------------------------------------------------------------------------

_HEAD_NS = 'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
_SEC_NS = (
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
    ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
    ' xmlns:ht="http://www.hancom.co.kr/hwpml/2011/table"'
)


def _hwpx(tmp_path: pathlib.Path, name: str, header: str, section: str) -> pathlib.Path:
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", header)
        zf.writestr("Contents/section0.xml", section)
    return path


def _header_with_numbering(num_id: str, num_format: str) -> str:
    """header.xml with one numbering definition and one paraPr referencing it."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<hh:head {_HEAD_NS} version="1.5" secCnt="1">'
        f'<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
        f'<hh:refList>'
        f'<hh:fontfaces itemCnt="0"/>'
        f'<hh:charProperties itemCnt="1">'
        f'<hh:charPr id="0" height="1000"/>'
        f'</hh:charProperties>'
        f'<hh:numberings itemCnt="1">'
        f'<hh:numbering id="{num_id}" start="1">'
        f'<hh:paraHead start="1" level="1" numFormat="{num_format}">^1.</hh:paraHead>'
        f'</hh:numbering>'
        f'</hh:numberings>'
        f'<hh:paraProperties itemCnt="1">'
        f'<hh:paraPr id="0">'
        f'<hh:heading type="NUMBER" idRef="{num_id}" level="0"/>'
        f'</hh:paraPr>'
        f'</hh:paraProperties>'
        f'<hh:styles itemCnt="0"/>'
        f'</hh:refList>'
        f'</hh:head>'
    )


def _header_legacy_autonum() -> str:
    """header.xml with a paraPr using the legacy autoNumFormat tag."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<hh:head {_HEAD_NS} version="1.5" secCnt="1">'
        f'<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
        f'<hh:refList>'
        f'<hh:fontfaces itemCnt="0"/>'
        f'<hh:charProperties itemCnt="1">'
        f'<hh:charPr id="0" height="1000"/>'
        f'</hh:charProperties>'
        f'<hh:paraProperties itemCnt="1">'
        f'<hh:paraPr id="0">'
        f'<hh:autoNumFormat numFormat="DIGIT"/>'
        f'</hh:paraPr>'
        f'</hh:paraProperties>'
        f'<hh:styles itemCnt="0"/>'
        f'</hh:refList>'
        f'</hh:head>'
    )


def _header_legacy_bullet() -> str:
    """header.xml with a paraPr using the legacy bullet tag."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<hh:head {_HEAD_NS} version="1.5" secCnt="1">'
        f'<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
        f'<hh:refList>'
        f'<hh:fontfaces itemCnt="0"/>'
        f'<hh:charProperties itemCnt="1">'
        f'<hh:charPr id="0" height="1000"/>'
        f'</hh:charProperties>'
        f'<hh:paraProperties itemCnt="1">'
        f'<hh:paraPr id="0">'
        f'<hh:bullet/>'
        f'</hh:paraPr>'
        f'</hh:paraProperties>'
        f'<hh:styles itemCnt="0"/>'
        f'</hh:refList>'
        f'</hh:head>'
    )


def _header_missing_ref() -> str:
    """header.xml with a paraPr referencing a numbering id that doesn't exist."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<hh:head {_HEAD_NS} version="1.5" secCnt="1">'
        f'<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
        f'<hh:refList>'
        f'<hh:fontfaces itemCnt="0"/>'
        f'<hh:charProperties itemCnt="1">'
        f'<hh:charPr id="0" height="1000"/>'
        f'</hh:charProperties>'
        f'<hh:paraProperties itemCnt="1">'
        f'<hh:paraPr id="0">'
        f'<hh:heading type="NUMBER" idRef="99" level="0"/>'
        f'</hh:paraPr>'
        f'</hh:paraProperties>'
        f'<hh:styles itemCnt="0"/>'
        f'</hh:refList>'
        f'</hh:head>'
    )


def _body_para(text: str, para_pr_id: str = "0") -> str:
    return (
        f'<hp:p paraPrIDRef="{para_pr_id}">'
        f'<hp:run charPrIDRef="0"><hp:t>{text}</hp:t></hp:run>'
        f'</hp:p>'
    )


def _body_table_with_para(text: str, para_pr_id: str = "0") -> str:
    return (
        '<ht:tbl numRows="1" numCols="1">'
        '<ht:tr>'
        '<ht:tc>'
        '<ht:subList>'
        f'<hp:p paraPrIDRef="{para_pr_id}">'
        f'<hp:run charPrIDRef="0"><hp:t>{text}</hp:t></hp:run>'
        f'</hp:p>'
        '</ht:subList>'
        '</ht:tc>'
        '</ht:tr>'
        '</ht:tbl>'
    )


def _section(*body_parts: str) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<hs:sec {_SEC_NS}>'
        + "".join(body_parts)
        + '</hs:sec>'
    )


# ---------------------------------------------------------------------------

class DescribeOrderedListInBody:

    def it_detects_list_ordered_from_digit_numformat(self, tmp_path):
        path = _hwpx(
            tmp_path, "ordered.hwpx",
            _header_with_numbering("1", "DIGIT"),
            _section(_body_para("item one")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_ORDERED

    def it_detects_list_ordered_from_latin_small_numformat(self, tmp_path):
        path = _hwpx(
            tmp_path, "ordered_latin.hwpx",
            _header_with_numbering("1", "LATIN_SMALL"),
            _section(_body_para("item a")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_ORDERED

    def it_detects_list_ordered_from_roman_small_numformat(self, tmp_path):
        path = _hwpx(
            tmp_path, "ordered_roman.hwpx",
            _header_with_numbering("1", "ROMAN_SMALL"),
            _section(_body_para("item i")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_ORDERED


class DescribeUnorderedListInBody:

    def it_detects_list_unordered_from_disc_numformat(self, tmp_path):
        path = _hwpx(
            tmp_path, "bullet_disc.hwpx",
            _header_with_numbering("1", "DISC"),
            _section(_body_para("bullet item")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_UNORDERED

    def it_detects_list_unordered_from_bullet_numformat(self, tmp_path):
        path = _hwpx(
            tmp_path, "bullet_bullet.hwpx",
            _header_with_numbering("1", "BULLET"),
            _section(_body_para("bullet item")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_UNORDERED

    def it_detects_list_unordered_from_circle_numformat(self, tmp_path):
        path = _hwpx(
            tmp_path, "bullet_circle.hwpx",
            _header_with_numbering("1", "CIRCLE"),
            _section(_body_para("bullet item")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_UNORDERED


class DescribeListInTableCell:

    def it_detects_ordered_list_inside_cell(self, tmp_path):
        path = _hwpx(
            tmp_path, "cell_ordered.hwpx",
            _header_with_numbering("1", "DIGIT"),
            _section(_body_table_with_para("cell item")),
        )
        doc = openhanji.open(path)
        assert len(doc.tables) == 1
        cell = doc.tables[0].rows[0].cells[0]
        paras = [b for b in cell.blocks if isinstance(b, Paragraph)]
        assert paras
        assert paras[0].style == ParagraphStyle.LIST_ORDERED

    def it_detects_unordered_list_inside_cell(self, tmp_path):
        path = _hwpx(
            tmp_path, "cell_bullet.hwpx",
            _header_with_numbering("1", "DISC"),
            _section(_body_table_with_para("cell bullet")),
        )
        doc = openhanji.open(path)
        cell = doc.tables[0].rows[0].cells[0]
        paras = [b for b in cell.blocks if isinstance(b, Paragraph)]
        assert paras[0].style == ParagraphStyle.LIST_UNORDERED


class DescribeLegacyListTags:

    def it_ordered_from_legacy_autoNumFormat(self, tmp_path):
        path = _hwpx(
            tmp_path, "legacy_autonum.hwpx",
            _header_legacy_autonum(),
            _section(_body_para("legacy ordered")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_ORDERED

    def it_unordered_from_legacy_bullet_tag(self, tmp_path):
        path = _hwpx(
            tmp_path, "legacy_bullet.hwpx",
            _header_legacy_bullet(),
            _section(_body_para("legacy bullet")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_UNORDERED


class DescribeMissingNumberingRef:

    def it_does_not_crash_on_missing_numbering_id(self, tmp_path):
        path = _hwpx(
            tmp_path, "missing_ref.hwpx",
            _header_missing_ref(),
            _section(_body_para("orphan list item")),
        )
        doc = openhanji.open(path)
        assert len(doc.paragraphs) == 1

    def it_falls_back_to_ordered_when_ref_missing(self, tmp_path):
        path = _hwpx(
            tmp_path, "missing_ref_style.hwpx",
            _header_missing_ref(),
            _section(_body_para("orphan")),
        )
        doc = openhanji.open(path)
        # missing ref → index.numbering.get(hidref, "ordered") → LIST_ORDERED
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_ORDERED


class DescribeBlockOrderPreserved:

    def it_block_count_unchanged_with_list_items(self, tmp_path):
        path = _hwpx(
            tmp_path, "order.hwpx",
            _header_with_numbering("1", "DIGIT"),
            _section(
                _body_para("item 1"),
                _body_para("item 2"),
                _body_para("item 3"),
            ),
        )
        doc = openhanji.open(path)
        assert len(doc.paragraphs) == 3

    def it_block_indices_are_sequential(self, tmp_path):
        path = _hwpx(
            tmp_path, "order_idx.hwpx",
            _header_with_numbering("1", "DIGIT"),
            _section(
                _body_para("item 1"),
                _body_para("item 2"),
            ),
        )
        doc = openhanji.open(path)
        assert [b.index for b in doc.blocks] == list(range(len(doc.blocks)))

    def it_text_content_unchanged(self, tmp_path):
        path = _hwpx(
            tmp_path, "order_text.hwpx",
            _header_with_numbering("1", "DIGIT"),
            _section(_body_para("list item text")),
        )
        doc = openhanji.open(path)
        assert doc.paragraphs[0].text == "list item text"


class DescribeHeadingDetectionNonePreservesLists:

    def it_list_survives_heading_detection_none(self, tmp_path):
        path = _hwpx(
            tmp_path, "none_mode_list.hwpx",
            _header_with_numbering("1", "DIGIT"),
            _section(_body_para("list item")),
        )
        doc = openhanji.open(path, heading_detection="none")
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_ORDERED

    def it_bullet_survives_heading_detection_none(self, tmp_path):
        path = _hwpx(
            tmp_path, "none_mode_bullet.hwpx",
            _header_with_numbering("1", "DISC"),
            _section(_body_para("bullet item")),
        )
        doc = openhanji.open(path, heading_detection="none")
        assert doc.paragraphs[0].style == ParagraphStyle.LIST_UNORDERED


class DescribeRealDocumentListDetection:
    """Regression tests against cv-headings-lists-equation-footer.hwpx."""

    FIXTURE = (
        pathlib.Path(__file__).parent.parent
        / "test_files" / "hwpx" / "lab_cv-headings-lists-equation-footer.hwpx"
    )

    def it_detects_ordered_lists_in_table_cells(self):
        doc = openhanji.open(self.FIXTURE)
        cell_lists = [
            b for tbl in doc.tables
            for row in tbl.rows
            for cell in row.cells
            for b in cell.blocks
            if isinstance(b, Paragraph) and b.style == ParagraphStyle.LIST_ORDERED
        ]
        assert len(cell_lists) >= 4

    def it_has_no_false_positive_list_in_plain_body(self):
        doc = openhanji.open(self.FIXTURE)
        # top-level body paragraphs should not be misclassified as lists
        body_lists = [
            p for p in doc.paragraphs
            if p.style in (ParagraphStyle.LIST_ORDERED, ParagraphStyle.LIST_UNORDERED)
        ]
        assert body_lists == []

    def it_service_proposal_has_41_ordered_list_paragraphs(self):
        path = (
            pathlib.Path(__file__).parent.parent
            / "test_files" / "hwpx" / "lab_service-proposal.hwpx"
        )
        doc = openhanji.open(path)
        lists = [p for p in doc.paragraphs if p.style == ParagraphStyle.LIST_ORDERED]
        assert len(lists) == 41
