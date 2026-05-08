"""Integration tests for the CLI (extract and info subcommands)."""

from __future__ import annotations

import json
import pathlib
import zipfile

import pytest
from click.testing import CliRunner

from openhanji.cli import main

TEST_FILES = pathlib.Path(__file__).parent.parent / "test_files"
BASIC = TEST_FILES / "hwpx" / "sxa_owpml-structure-coverage.hwpx"
BUSINESS = TEST_FILES / "hwpx" / "sxa_business-plan-90p-19tbl-7img.hwpx"


@pytest.fixture()
def runner():
    return CliRunner()


#extract markdown

class TestExtractMarkdown:
    def test_default_format_is_markdown(self, runner):
        result = runner.invoke(main, ["extract", str(BASIC)])
        assert result.exit_code == 0
        assert len(result.output) > 0

    def test_explicit_markdown_flag(self, runner):
        result = runner.invoke(main, ["extract", str(BASIC), "--format", "markdown"])
        assert result.exit_code == 0
        assert "#" in result.output or "|" in result.output

    def test_business_plan_markdown(self, runner):
        result = runner.invoke(main, ["extract", str(BUSINESS), "-f", "markdown"])
        assert result.exit_code == 0
        assert len(result.output) > 100


#extract json

class TestExtractJson:
    def test_json_is_valid(self, runner):
        result = runner.invoke(main, ["extract", str(BASIC), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "metadata" in data
        assert "body" in data

    def test_json_body_has_items(self, runner):
        result = runner.invoke(main, ["extract", str(BUSINESS), "-f", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["body"]) > 0

    def test_json_types_valid(self, runner):
        result = runner.invoke(main, ["extract", str(BASIC), "-f", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        types = {item["type"] for item in data["body"]}
        assert types <= {"paragraph", "table", "image"}


#extract text

class TestExtractText:
    def test_text_output(self, runner):
        result = runner.invoke(main, ["extract", str(BASIC), "--format", "text"])
        assert result.exit_code == 0
        assert len(result.output) > 0

    def test_business_text(self, runner):
        result = runner.invoke(main, ["extract", str(BUSINESS), "-f", "text"])
        assert result.exit_code == 0
        assert len(result.output) > 0


#extract to file

class TestExtractToFile:
    def test_writes_to_file(self, runner, tmp_path):
        out = tmp_path / "output.md"
        result = runner.invoke(main, ["extract", str(BASIC), "--out", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert len(out.read_text(encoding="utf-8")) > 0

    def test_json_to_file(self, runner, tmp_path):
        out = tmp_path / "output.json"
        result = runner.invoke(
            main, ["extract", str(BASIC), "-f", "json", "-o", str(out)]
        )
        assert result.exit_code == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "body" in data


#extract errors

class TestExtractErrors:
    def test_missing_file_exits_nonzero(self, runner):
        result = runner.invoke(main, ["extract", "/nonexistent/path/file.hwpx"])
        assert result.exit_code != 0

    def test_corrupted_file_exits_nonzero(self, runner, tmp_path):
        bad = tmp_path / "bad.hwpx"
        bad.write_bytes(b"not a zip")
        result = runner.invoke(main, ["extract", str(bad)])
        assert result.exit_code != 0

    def test_strict_on_valid_file_succeeds(self, runner):
        result = runner.invoke(main, ["extract", str(BASIC), "--strict"])
        assert result.exit_code == 0

    def test_strict_on_bad_xml_exits_nonzero(self, runner, tmp_path):
        path = tmp_path / "badxml.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("content.hpf", "<package/>")
            zf.writestr("Contents/section0.xml", "<<bad xml>>")
        result = runner.invoke(main, ["extract", str(path), "--strict"])
        assert result.exit_code != 0


#info

class TestInfo:
    def test_info_basic(self, runner):
        result = runner.invoke(main, ["info", str(BASIC)])
        assert result.exit_code == 0
        assert "Paragraphs" in result.output
        assert "Tables" in result.output
        assert "Images" in result.output

    def test_info_business_plan(self, runner):
        result = runner.invoke(main, ["info", str(BUSINESS)])
        assert result.exit_code == 0
        assert "90" in result.output   # paragraphs
        assert "19" in result.output   # tables
        assert "7" in result.output    # images

    def test_info_shows_metadata_fields(self, runner):
        result = runner.invoke(main, ["info", str(BASIC)])
        assert result.exit_code == 0
        for field in ("Title", "Author"):
            assert field in result.output
        for field in ("Created", "Modified", "Pages"):
            assert field not in result.output

    def test_info_omits_missing_metadata_values(self, runner, tmp_path):
        path = tmp_path / "bare.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr(
                "Contents/header.xml",
                '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"/>',
            )
            zf.writestr(
                "Contents/section0.xml",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
                ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
                '<hp:p><hp:run><hp:t>x</hp:t></hp:run></hp:p>'
                '</hs:sec>',
            )
        result = runner.invoke(main, ["info", str(path)])
        assert result.exit_code == 0
        assert "Title" not in result.output
        assert "Author" not in result.output
        assert "Paragraphs" in result.output

    def test_info_missing_file_exits_nonzero(self, runner):
        result = runner.invoke(main, ["info", "/nonexistent/file.hwpx"])
        assert result.exit_code != 0


#version

def test_version_flag(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1" in result.output


#batch directory mode

class TestExtractDirectory:
    def test_directory_requires_out(self, runner, tmp_path):
        result = runner.invoke(main, ["extract", str(TEST_FILES / "hwpx")])
        assert result.exit_code != 0
        assert "--out" in result.output or "--out" in (result.output + (result.exception or ""))

    def test_directory_writes_files(self, runner, tmp_path):
        out_dir = tmp_path / "out"
        result = runner.invoke(
            main, ["extract", str(TEST_FILES / "hwpx"), "--format", "markdown", "--out", str(out_dir)]
        )
        assert result.exit_code == 0
        md_files = list(out_dir.glob("*.md"))
        assert len(md_files) >= 2

    def test_directory_json_format(self, runner, tmp_path):
        out_dir = tmp_path / "out"
        result = runner.invoke(
            main, ["extract", str(TEST_FILES / "hwpx"), "--format", "json", "--out", str(out_dir)]
        )
        assert result.exit_code == 0
        json_files = list(out_dir.glob("*.json"))
        assert len(json_files) >= 2
        for f in json_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            assert "body" in data

    def test_directory_text_format(self, runner, tmp_path):
        out_dir = tmp_path / "out"
        result = runner.invoke(
            main, ["extract", str(TEST_FILES / "hwpx"), "--format", "text", "--out", str(out_dir)]
        )
        assert result.exit_code == 0
        txt_files = list(out_dir.glob("*.txt"))
        assert len(txt_files) >= 2

    def test_directory_creates_out_dir(self, runner, tmp_path):
        out_dir = tmp_path / "nested" / "out"
        assert not out_dir.exists()
        result = runner.invoke(
            main, ["extract", str(TEST_FILES / "hwpx"), "--out", str(out_dir)]
        )
        assert result.exit_code == 0
        assert out_dir.exists()

    def test_empty_directory_exits_nonzero(self, runner, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        out_dir = tmp_path / "out"
        result = runner.invoke(
            main, ["extract", str(empty_dir), "--out", str(out_dir)]
        )
        assert result.exit_code != 0
