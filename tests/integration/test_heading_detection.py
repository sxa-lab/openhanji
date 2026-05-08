"""Tests for the heading_detection parser option.

Uses the same minimal HWPX builder as test_parser_fixes.py.
"""

import pathlib
import zipfile

import pytest

import openhanji
from openhanji.document import ParagraphStyle


def _make_hwpx(
    tmp_path: pathlib.Path,
    font_face: str,
    font_size_hwpunit: int,
    bold: bool,
    text: str,
    outline_level: str = "",
    name: str = "para.hwpx",
) -> pathlib.Path:
    bold_val = "1" if bold else "0"
    outline_attr = f' outlineLevel="{outline_level}"' if outline_level else ""
    header = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
        ' version="1.5" secCnt="1">'
        '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
        '<hh:refList>'
        '<hh:fontfaces itemCnt="1">'
        '<hh:fontface lang="HANGUL" fontCnt="1">'
        f'<hh:font id="0" face="{font_face}"/>'
        '</hh:fontface>'
        '</hh:fontfaces>'
        '<hh:charProperties itemCnt="1">'
        f'<hh:charPr id="0" height="{font_size_hwpunit}" bold="{bold_val}">'
        '<hh:fontRef hangul="0" latin="0"/>'
        '</hh:charPr>'
        '</hh:charProperties>'
        '<hh:paraProperties itemCnt="1">'
        f'<hh:paraPr id="0"{outline_attr}/>'
        '</hh:paraProperties>'
        '<hh:styles itemCnt="0"/>'
        '</hh:refList>'
        '</hh:head>'
    )
    section = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
        ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        '<hp:p paraPrIDRef="0">'
        '<hp:run charPrIDRef="0">'
        f'<hp:t>{text}</hp:t>'
        '</hp:run>'
        '</hp:p>'
        '</hs:sec>'
    )
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", header)
        zf.writestr("Contents/section0.xml", section)
    return path


class DescribeHeadingDetectionNone:

    def it_forces_all_paragraphs_to_body(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "대제목")
        doc = openhanji.open(path, heading_detection="none")
        assert len(doc.paragraphs) == 1
        assert doc.paragraphs[0].style == ParagraphStyle.BODY

    def it_suppresses_structural_outline_level_too(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(tmp_path, "맑은 고딕", 1000, False, "개요제목", outline_level="1")
        doc = openhanji.open(path, heading_detection="none")
        assert doc.paragraphs[0].style == ParagraphStyle.BODY

    def it_preserves_list_detection(self, tmp_path: pathlib.Path) -> None:
        # lists come from paraPr list_kind, not the heading branch —
        # heading_detection="none" should not suppress list detection.
        # This document has no list markup, so BODY is expected here;
        # the test confirms no crash and no heading.
        path = _make_hwpx(tmp_path, "맑은 고딕", 1000, False, "목록 항목")
        doc = openhanji.open(path, heading_detection="none")
        assert doc.paragraphs[0].style in (ParagraphStyle.BODY, ParagraphStyle.LIST_UNORDERED, ParagraphStyle.LIST_ORDERED)


class DescribeHeadingDetectionStructural:

    def it_does_not_fire_font_heuristic(self, tmp_path: pathlib.Path) -> None:
        # HY헤드라인M at 20pt would be HEADING1 under "auto"
        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "큰 글씨")
        doc = openhanji.open(path, heading_detection="structural")
        assert doc.paragraphs[0].style == ParagraphStyle.BODY

    def it_still_respects_outline_level(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(tmp_path, "맑은 고딕", 1000, False, "개요1", outline_level="1")
        doc = openhanji.open(path, heading_detection="structural")
        assert doc.paragraphs[0].style == ParagraphStyle.HEADING1

    def it_still_respects_outline_level_2(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(tmp_path, "맑은 고딕", 1000, False, "개요2", outline_level="2")
        doc = openhanji.open(path, heading_detection="structural")
        assert doc.paragraphs[0].style == ParagraphStyle.HEADING2


class DescribeHeadingDetectionAuto:

    def it_fires_font_heuristic_for_heading_face(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "대제목")
        doc = openhanji.open(path, heading_detection="auto")
        assert doc.paragraphs[0].style == ParagraphStyle.HEADING1

    def it_does_not_promote_non_bold_body_font(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(tmp_path, "맑은 고딕", 2000, False, "큰 본문")
        doc = openhanji.open(path, heading_detection="auto")
        assert doc.paragraphs[0].style == ParagraphStyle.BODY


class DescribeCliHeadingDetection:

    def it_passes_through_none_mode(self, tmp_path: pathlib.Path) -> None:
        from click.testing import CliRunner
        from openhanji.cli import main

        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "대제목")
        result = CliRunner().invoke(main, ["extract", str(path), "--heading-detection", "none"])
        assert result.exit_code == 0
        assert "# 대제목" not in result.output

    def it_passes_through_structural_mode(self, tmp_path: pathlib.Path) -> None:
        from click.testing import CliRunner
        from openhanji.cli import main

        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "대제목")
        result = CliRunner().invoke(main, ["extract", str(path), "--heading-detection", "structural"])
        assert result.exit_code == 0
        assert "# 대제목" not in result.output

    def it_auto_mode_produces_heading(self, tmp_path: pathlib.Path) -> None:
        from click.testing import CliRunner
        from openhanji.cli import main

        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "대제목")
        result = CliRunner().invoke(main, ["extract", str(path)])
        assert result.exit_code == 0
        assert "# 대제목" in result.output
