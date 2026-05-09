"""Integration tests for the CLI (extract and info subcommands)."""

from __future__ import annotations

import json
import pathlib
import shutil
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


# extract markdown


class TestExtractMarkdown:
    def test_default_format_is_markdown(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BASIC)])
            assert result.exit_code == 0
            md_files = list(pathlib.Path(".").glob("*.md"))
            assert len(md_files) == 1
            assert len(md_files[0].read_text()) > 0

    def test_explicit_markdown_flag(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BASIC), "--format", "markdown"])
            assert result.exit_code == 0
            md_files = list(pathlib.Path(".").glob("*.md"))
            assert len(md_files) == 1
            content = md_files[0].read_text()
            assert "#" in content or "|" in content

    def test_business_plan_markdown(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BUSINESS), "-f", "markdown"])
            assert result.exit_code == 0
            md_files = list(pathlib.Path(".").glob("*.md"))
            assert len(md_files) == 1
            assert len(md_files[0].read_text()) > 100


# extract json


class TestExtractJson:
    def test_json_is_valid(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BASIC), "--format", "json"])
            assert result.exit_code == 0
            json_files = list(pathlib.Path(".").glob("*.json"))
            assert len(json_files) == 1
            data = json.loads(json_files[0].read_text())
            assert "metadata" in data
            assert "body" in data

    def test_json_body_has_items(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BUSINESS), "-f", "json"])
            assert result.exit_code == 0
            json_files = list(pathlib.Path(".").glob("*.json"))
            assert len(json_files) == 1
            data = json.loads(json_files[0].read_text())
            assert len(data["body"]) > 0

    def test_json_types_valid(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BASIC), "-f", "json"])
            assert result.exit_code == 0
            json_files = list(pathlib.Path(".").glob("*.json"))
            data = json.loads(json_files[0].read_text())
            types = {item["type"] for item in data["body"]}
            assert types <= {"paragraph", "table", "image"}


# extract text


class TestExtractText:
    def test_text_output(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BASIC), "--format", "text"])
            assert result.exit_code == 0
            txt_files = list(pathlib.Path(".").glob("*.txt"))
            assert len(txt_files) == 1
            assert len(txt_files[0].read_text()) > 0

    def test_business_text(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BUSINESS), "-f", "text"])
            assert result.exit_code == 0
            txt_files = list(pathlib.Path(".").glob("*.txt"))
            assert len(txt_files) == 1
            assert len(txt_files[0].read_text()) > 0


# extract to explicit file


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

    def test_explicit_path_refuses_if_exists(self, runner, tmp_path):
        """Explicit --out <file> that already exists exits 1, never overwrites."""
        out = tmp_path / "output.md"
        out.write_text("original content", encoding="utf-8")
        result = runner.invoke(main, ["extract", str(BASIC), "--out", str(out)])
        assert result.exit_code != 0
        assert out.read_text(encoding="utf-8") == "original content"


# single-file output placement


class TestExtractSingleFileOutput:
    def test_no_out_writes_to_cwd(self, runner):
        """Single-file extract without --out writes to CWD."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BASIC)])
            assert result.exit_code == 0
            md_files = list(pathlib.Path(".").glob("*.md"))
            assert len(md_files) == 1

    def test_no_out_filename_scheme(self, runner):
        """Output filename is stem_ext.fmt."""
        with runner.isolated_filesystem():
            runner.invoke(main, ["extract", str(BASIC)])
            names = [f.name for f in pathlib.Path(".").glob("*.md")]
            assert any("_hwpx" in n for n in names)

    def test_out_as_directory_places_file_inside(self, runner, tmp_path):
        """--out pointing to a directory places the file inside it."""
        result = runner.invoke(
            main, ["extract", str(BASIC), "--out", str(tmp_path)]
        )
        assert result.exit_code == 0
        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) == 1

    def test_collision_increments_counter(self, runner, tmp_path):
        """Second run with same input increments to (1) instead of overwriting."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        runner.invoke(main, ["extract", str(BASIC), "--out", str(out_dir)])
        runner.invoke(main, ["extract", str(BASIC), "--out", str(out_dir)])
        files = list(out_dir.glob("*.md"))
        assert len(files) == 2
        names = {f.name for f in files}
        assert any("(1)" in n for n in names)


# extract errors


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
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BASIC), "--strict"])
            assert result.exit_code == 0

    def test_strict_on_bad_xml_exits_nonzero(self, runner, tmp_path):
        path = tmp_path / "badxml.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("content.hpf", "<package/>")
            zf.writestr("Contents/section0.xml", "<<bad xml>>")
        result = runner.invoke(main, ["extract", str(path), "--strict"])
        assert result.exit_code != 0


# info


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
        assert "90" in result.output  # paragraphs
        assert "19" in result.output  # tables
        assert "7" in result.output  # images

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
                "<hp:p><hp:run><hp:t>x</hp:t></hp:run></hp:p>"
                "</hs:sec>",
            )
        result = runner.invoke(main, ["info", str(path)])
        assert result.exit_code == 0
        assert "Title" not in result.output
        assert "Author" not in result.output
        assert "Paragraphs" in result.output

    def test_info_missing_file_exits_nonzero(self, runner):
        result = runner.invoke(main, ["info", "/nonexistent/file.hwpx"])
        assert result.exit_code != 0


# version


def test_version_flag(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1" in result.output


# batch directory mode


class TestExtractDirectory:
    def test_directory_writes_files(self, runner, tmp_path):
        out_dir = tmp_path / "out"
        result = runner.invoke(
            main,
            [
                "extract",
                str(TEST_FILES / "hwpx"),
                "--format",
                "markdown",
                "--out",
                str(out_dir),
            ],
        )
        assert result.exit_code == 0
        md_files = list(out_dir.glob("*.md"))
        assert len(md_files) >= 2

    def test_directory_json_format(self, runner, tmp_path):
        out_dir = tmp_path / "out"
        result = runner.invoke(
            main,
            [
                "extract",
                str(TEST_FILES / "hwpx"),
                "--format",
                "json",
                "--out",
                str(out_dir),
            ],
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
            main,
            [
                "extract",
                str(TEST_FILES / "hwpx"),
                "--format",
                "text",
                "--out",
                str(out_dir),
            ],
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
        result = runner.invoke(main, ["extract", str(empty_dir), "--out", str(out_dir)])
        assert result.exit_code != 0


class TestExtractBatchFlags:
    def test_verbose_prints_progress(self, runner, tmp_path):
        """--verbose prints per-file progress and a Done summary."""
        out = tmp_path / "out"
        result = runner.invoke(
            main,
            ["extract", str(TEST_FILES / "hwpx"), "--out", str(out), "--verbose"],
        )
        assert result.exit_code == 0
        assert "[ok]" in result.output
        assert "Done:" in result.output

    def test_types_filter_hwpx_only(self, runner, tmp_path):
        """--types hwpx limits processing to .hwpx files only."""
        out = tmp_path / "out"
        result = runner.invoke(
            main,
            ["extract", str(TEST_FILES / "hwpx"), "--out", str(out), "--types", "hwpx"],
        )
        assert result.exit_code == 0
        assert "Done:" in result.output

    def test_types_unknown_extension_exits_nonzero(self, runner, tmp_path):
        """--types with an unknown extension prints error and exits 1."""
        out = tmp_path / "out"
        result = runner.invoke(
            main,
            ["extract", str(TEST_FILES / "hwpx"), "--out", str(out), "--types", "xyz"],
        )
        assert result.exit_code == 1
        assert "unknown type" in result.output.lower()

    def test_summary_line_without_verbose(self, runner, tmp_path):
        """Done: summary always prints even without --verbose."""
        out = tmp_path / "out"
        result = runner.invoke(
            main,
            ["extract", str(TEST_FILES / "hwpx"), "--out", str(out)],
        )
        assert result.exit_code == 0
        assert "Done:" in result.output

    def test_collision_safe_output_names(self, runner, tmp_path):
        """Output filenames use stem_ext scheme to avoid collisions."""
        out = tmp_path / "out"
        runner.invoke(
            main,
            ["extract", str(TEST_FILES / "hwpx"), "--out", str(out)],
        )
        for f in out.iterdir():
            assert "_hwpx" in f.name, (
                f"Expected collision-safe name like 'foo_hwpx.md', got: {f.name}"
            )


# mixed-type batch


class TestExtractMixedBatch:
    def test_no_out_defaults_to_extracted(self, runner):
        """Directory mode without --out writes to ./extracted/."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(TEST_FILES / "hwpx")])
            assert result.exit_code == 0
            assert pathlib.Path("extracted").is_dir()

    def test_same_type_batch_is_flat(self, runner, tmp_path):
        """All-.hwpx batch produces flat output (no subfolders)."""
        out = tmp_path / "out"
        runner.invoke(
            main,
            ["extract", str(TEST_FILES / "hwpx"), "--out", str(out), "--types", "hwpx"],
        )
        assert not (out / "hwpx").is_dir()
        assert len(list(out.glob("*.md"))) >= 1

    def test_mixed_type_batch_uses_subfolders(self, runner, tmp_path):
        """present_exts > 1 triggers per-type subfolder structure."""
        mixed = tmp_path / "mixed"
        mixed.mkdir()
        shutil.copy(BASIC, mixed / "a.hwpx")
        # rename a copy to .cell at filesystem level — tests subfolder logic
        # without depending on .cell format support
        shutil.copy(BASIC, mixed / "b.hwpx")
        (mixed / "b.hwpx").rename(mixed / "b.cell")
        out = tmp_path / "out"
        # b.cell raises NotSupportedError (skipped); a.hwpx succeeds
        runner.invoke(main, ["extract", str(mixed), "--out", str(out)])
        assert (out / "hwpx").is_dir()
        assert len(list((out / "hwpx").glob("*.md"))) == 1
