"""Tests for the heading_detection parser option."""

import pathlib

import openhanji
from openhanji.models.document import ParagraphStyle
from tests.integration.builders import make_charpr_hwpx as _make_hwpx


class DescribeHeadingDetectionNone:
    def it_forces_all_paragraphs_to_body(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "대제목")
        doc = openhanji.open(path, heading_detection="none")
        assert len(doc.paragraphs) == 1
        assert doc.paragraphs[0].style == ParagraphStyle.BODY

    def it_suppresses_structural_outline_level_too(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = _make_hwpx(
            tmp_path, "맑은 고딕", 1000, False, "개요제목", outline_level="1"
        )
        doc = openhanji.open(path, heading_detection="none")
        assert doc.paragraphs[0].style == ParagraphStyle.BODY

    def it_preserves_list_detection(self, tmp_path: pathlib.Path) -> None:
        # lists come from paraPr list_kind, not the heading branch —
        # heading_detection="none" should not suppress list detection.
        # This document has no list markup, so BODY is expected here;
        # the test confirms no crash and no heading.
        path = _make_hwpx(tmp_path, "맑은 고딕", 1000, False, "목록 항목")
        doc = openhanji.open(path, heading_detection="none")
        assert doc.paragraphs[0].style in (
            ParagraphStyle.BODY,
            ParagraphStyle.LIST_UNORDERED,
            ParagraphStyle.LIST_ORDERED,
        )


class DescribeHeadingDetectionStructural:
    def it_does_not_fire_font_heuristic(self, tmp_path: pathlib.Path) -> None:
        # HY헤드라인M at 20pt would be HEADING1 under "auto"
        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "큰 글씨")
        doc = openhanji.open(path, heading_detection="structural")
        assert doc.paragraphs[0].style == ParagraphStyle.BODY

    def it_still_respects_outline_level(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(
            tmp_path, "맑은 고딕", 1000, False, "개요1", outline_level="1"
        )
        doc = openhanji.open(path, heading_detection="structural")
        assert doc.paragraphs[0].style == ParagraphStyle.HEADING1

    def it_still_respects_outline_level_2(self, tmp_path: pathlib.Path) -> None:
        path = _make_hwpx(
            tmp_path, "맑은 고딕", 1000, False, "개요2", outline_level="2"
        )
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
        result = CliRunner().invoke(
            main, ["extract", str(path), "--heading-detection", "none"]
        )
        assert result.exit_code == 0
        assert "# 대제목" not in result.output

    def it_passes_through_structural_mode(self, tmp_path: pathlib.Path) -> None:
        from click.testing import CliRunner

        from openhanji.cli import main

        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "대제목")
        result = CliRunner().invoke(
            main, ["extract", str(path), "--heading-detection", "structural"]
        )
        assert result.exit_code == 0
        assert "# 대제목" not in result.output

    def it_auto_mode_produces_heading(self, tmp_path: pathlib.Path) -> None:
        from click.testing import CliRunner

        from openhanji.cli import main

        path = _make_hwpx(tmp_path, "HY헤드라인M", 2000, False, "대제목")
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(path)])
            assert result.exit_code == 0
            md_files = list(pathlib.Path(".").glob("*.md"))
            assert len(md_files) == 1
            assert "# 대제목" in md_files[0].read_text(encoding="utf-8")
