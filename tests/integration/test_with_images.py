"""Integration tests for the with_images flag (default=False, opt-in)."""

import json
import pathlib
import zipfile

from click.testing import CliRunner

import openhanji
from openhanji.cli import main
from openhanji.converters.json import to_json

TEST_FILES = pathlib.Path(__file__).parent.parent / "test_files"
BUSINESS = TEST_FILES / "hwpx" / "sxa_business-plan-90p-19tbl-7img.hwpx"


class DescribeDefaultBehavior:
    def it_produces_no_image_data_by_default(self):
        doc = openhanji.open(BUSINESS)
        assert doc.images
        assert all(img.data is None for img in doc.images)

    def it_produces_no_image_format_by_default(self):
        doc = openhanji.open(BUSINESS)
        assert all(img.format is None for img in doc.images)

    def it_preserves_image_structure_by_default(self):
        doc = openhanji.open(BUSINESS)
        assert len(doc.images) > 0

    def it_emits_placeholder_in_markdown_by_default(self):
        doc = openhanji.open(BUSINESS)
        md = doc.to_markdown()
        assert "data:image/" not in md
        assert "](image_" in md

    def it_emits_null_data_in_json_by_default(self):
        doc = openhanji.open(BUSINESS)
        data = json.loads(to_json(doc))
        images = [b for b in data["body"] if b["type"] == "image"]
        assert images
        assert all(b["data"] is None for b in images)


class DescribeWithImagesEnabled:
    def it_loads_image_binaries(self):
        doc = openhanji.open(BUSINESS, with_images=True)
        assert any(img.data is not None for img in doc.images)

    def it_sets_image_format(self):
        doc = openhanji.open(BUSINESS, with_images=True)
        assert any(img.format is not None for img in doc.images)

    def it_emits_data_uri_in_markdown(self):
        doc = openhanji.open(BUSINESS, with_images=True)
        md = doc.to_markdown()
        assert "data:image/" in md

    def it_emits_base64_data_in_json(self):
        doc = openhanji.open(BUSINESS, with_images=True)
        data = json.loads(to_json(doc))
        images = [b for b in data["body"] if b["type"] == "image"]
        assert any(isinstance(b["data"], str) for b in images)


class DescribeCliWithImagesFlag:
    def it_produces_no_data_uri_by_default(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BUSINESS), "-f", "markdown"])
            assert result.exit_code == 0
            content = list(pathlib.Path(".").glob("*.md"))[0].read_text()
            assert "data:image/" not in content

    def it_produces_data_uri_with_flag(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["extract", str(BUSINESS), "-f", "markdown", "--with-images"]
            )
            assert result.exit_code == 0
            content = list(pathlib.Path(".").glob("*.md"))[0].read_text()
            assert "data:image/" in content

    def it_json_default_has_null_data(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["extract", str(BUSINESS), "-f", "json"])
            assert result.exit_code == 0
            data = json.loads(list(pathlib.Path(".").glob("*.json"))[0].read_text())
            images = [b for b in data["body"] if b["type"] == "image"]
            assert images
            assert all(b["data"] is None for b in images)

    def it_json_with_flag_has_base64_data(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["extract", str(BUSINESS), "-f", "json", "--with-images"]
            )
            assert result.exit_code == 0
            data = json.loads(list(pathlib.Path(".").glob("*.json"))[0].read_text())
            images = [b for b in data["body"] if b["type"] == "image"]
            assert any(isinstance(b["data"], str) for b in images)


def _make_two_image_hwpx(tmp_path: pathlib.Path) -> pathlib.Path:
    """Build a minimal HWPX with two images in separate table cells."""
    # Each image gets a unique binary entry; BinData links via binaryItemIDRef.
    png1 = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])  # PNG magic
    png2 = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00])
    header = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
        ' version="1.5" secCnt="1">'
        '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
        "<hh:refList>"
        '<hh:fontfaces itemCnt="0"/>'
        '<hh:charProperties itemCnt="1">'
        '<hh:charPr id="0" height="1000"><hh:fontRef hangul="0" latin="0"/></hh:charPr>'
        "</hh:charProperties>"
        '<hh:paraProperties itemCnt="1"><hh:paraPr id="0"/></hh:paraProperties>'
        '<hh:styles itemCnt="0"/>'
        '<hh:binData itemCnt="2">'
        '<hh:binItem id="1" type="EMBED" format="png" name="BIN0001.png"/>'
        '<hh:binItem id="2" type="EMBED" format="png" name="BIN0002.png"/>'
        "</hh:binData>"
        "</hh:refList>"
        "</hh:head>"
    )
    # Two cells, each containing one picture inline object (no ctrl wrapper)
    section = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
        ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
        ' xmlns:ht="http://www.hancom.co.kr/hwpml/2011/table">'
        '<hp:p paraPrIDRef="0">'
        '<hp:run charPrIDRef="0">'
        "<ht:tbl>"
        "<ht:tr>"
        '<ht:tc><hp:p paraPrIDRef="0"><hp:run charPrIDRef="0">'
        '<hp:pic><hp:img binaryItemIDRef="1" width="1000" height="1000"/></hp:pic>'
        "</hp:run></hp:p></ht:tc>"
        '<ht:tc><hp:p paraPrIDRef="0"><hp:run charPrIDRef="0">'
        '<hp:pic><hp:img binaryItemIDRef="2" width="1000" height="1000"/></hp:pic>'
        "</hp:run></hp:p></ht:tc>"
        "</ht:tr>"
        "</ht:tbl>"
        "</hp:run>"
        "</hp:p>"
        "</hs:sec>"
    )
    path = tmp_path / "two_images.hwpx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", header)
        zf.writestr("Contents/section0.xml", section)
        zf.writestr("BinData/BIN0001.png", png1)
        zf.writestr("BinData/BIN0002.png", png2)
    return path


def _make_body_and_footer_image_hwpx(tmp_path: pathlib.Path) -> pathlib.Path:
    """Build a minimal HWPX with one body image and one footer image."""
    header = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
        ' version="1.5" secCnt="1">'
        '<hh:refList><hh:charProperties itemCnt="1">'
        '<hh:charPr id="0" height="1000"><hh:fontRef hangul="0" latin="0"/></hh:charPr>'
        "</hh:charProperties>"
        '<hh:paraProperties itemCnt="1"><hh:paraPr id="0"/></hh:paraProperties>'
        '<hh:styles itemCnt="0"/></hh:refList>'
        "</hh:head>"
    )
    section = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
        ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        '<hp:p paraPrIDRef="0"><hp:run charPrIDRef="0">'
        '<hp:pic title="body"><hp:img binaryItemIDRef="1"/></hp:pic>'
        "</hp:run></hp:p>"
        "<hp:ctrl><hp:footer><hp:subList>"
        '<hp:p paraPrIDRef="0"><hp:run charPrIDRef="0">'
        '<hp:pic title="footer"><hp:img binaryItemIDRef="2"/></hp:pic>'
        "</hp:run></hp:p>"
        "</hp:subList></hp:footer></hp:ctrl>"
        "</hs:sec>"
    )
    path = tmp_path / "body_footer_images.hwpx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", header)
        zf.writestr("Contents/section0.xml", section)
    return path


def _collect_cell_images(doc) -> list:
    """Collect all ImageRef nodes from inside table cells (not just top-level)."""
    from openhanji.models.document import ImageRef, Table

    images = []
    for item in doc.blocks:
        if isinstance(item, Table):
            for row in item.rows:
                for cell in row.cells:
                    for block in cell.blocks:
                        if isinstance(block, ImageRef):
                            images.append(block)
    return images


class DescribeImageSeqUniqueness:
    """Regression: images in separate table cells must get distinct image_seq values.

    Before _reindex_images was added, each cell's images were counted locally
    starting from 0, so two images in two cells both got image_seq=0 and the
    markdown rendered two src="image_0" placeholders.
    """

    def it_assigns_distinct_image_seq_to_images_in_separate_cells(self, tmp_path):
        path = _make_two_image_hwpx(tmp_path)
        doc = openhanji.open(path)
        images = _collect_cell_images(doc)
        assert len(images) == 2
        assert images[0].image_seq != images[1].image_seq, (
            f"both images got image_seq={images[0].image_seq}"
        )

    def it_assigns_seq_zero_and_one(self, tmp_path):
        path = _make_two_image_hwpx(tmp_path)
        doc = openhanji.open(path)
        images = _collect_cell_images(doc)
        seqs = sorted(img.image_seq for img in images)
        assert seqs == [0, 1]

    def it_emits_distinct_placeholder_names_in_html_table(self, tmp_path):
        path = _make_two_image_hwpx(tmp_path)
        doc = openhanji.open(path)
        md = doc.to_markdown()
        assert 'src="image_0"' in md
        assert 'src="image_1"' in md

    def it_assigns_distinct_image_seq_to_footer_images(self, tmp_path):
        path = _make_body_and_footer_image_hwpx(tmp_path)
        doc = openhanji.open(path)
        images = [doc.images[0], doc.footers[0]]
        assert sorted(img.image_seq for img in images) == [0, 1]
