"""Integration tests — run HwpxParser against synthetic HWPX test files.

Test files:
  tests/test_files/hwpx/sxa_owpml-structure-coverage.hwpx
  tests/test_files/hwpx/sxa_business-plan-90p-19tbl-7img.hwpx
"""

from __future__ import annotations

import json
import logging
import pathlib
import zipfile

import pytest

import openhanji
from openhanji.converters.json import to_json
from openhanji.exceptions import CorruptedFileError
from openhanji.models.document import Document, ImageRef, ParagraphStyle
from tests.integration.builders import assert_block_indices_sequential, make_hwpx, sec

TEST_FILES = pathlib.Path(__file__).parent.parent / "test_files"
BASIC = TEST_FILES / "hwpx" / "sxa_owpml-structure-coverage.hwpx"
BUSINESS = TEST_FILES / "hwpx" / "sxa_business-plan-90p-19tbl-7img.hwpx"


# helpers


def _open(path: pathlib.Path, strict: bool = False) -> Document:
    return openhanji.open(path, strict=strict)


# sxa_owpml-structure-coverage.hwpx


class TestBasicDocument:
    """Known counts: 18 paragraphs, 2 tables, 2 images, 22 body items."""

    @pytest.fixture(scope="class")
    def doc(self):
        return _open(BASIC)

    @pytest.fixture(scope="class")
    def doc_strict(self):
        return _open(BASIC, strict=True)

    def test_returns_document(self, doc):
        assert isinstance(doc, Document)

    def test_paragraph_count(self, doc):
        assert len(doc.paragraphs) == 18

    def test_table_count(self, doc):
        assert len(doc.tables) == 2

    def test_image_count(self, doc):
        assert len(doc.images) == 2

    def test_body_count(self, doc):
        assert len(doc.blocks) == 22

    def test_paragraphs_have_text(self, doc):
        for para in doc.paragraphs:
            assert isinstance(para.text, str)
            assert len(para.text) > 0

    def test_table_structure(self, doc):
        for table in doc.tables:
            assert len(table.rows) > 0
            for row in table.rows:
                assert len(row.cells) > 0

    def test_body_indices_are_unique(self, doc):
        indices = [item.index for item in doc.blocks]
        assert len(indices) == len(set(indices))

    def test_to_json_roundtrip(self, doc):
        data = json.loads(to_json(doc))
        assert "metadata" in data
        assert "body" in data
        assert isinstance(data["body"], list)
        assert len(data["body"]) > 0

    def test_to_markdown_produces_output(self, doc):
        md = doc.to_markdown()
        assert isinstance(md, str)
        assert len(md) > 0

    def test_to_markdown_has_gfm_table(self, doc):
        md = doc.to_markdown()
        assert "|" in md
        assert "---" in md

    def test_to_text_produces_output(self, doc):
        text = doc.to_text()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_metadata_is_metadata_object(self, doc):
        from openhanji.models.document import Metadata

        assert isinstance(doc.metadata, Metadata)

    def test_strict_mode_does_not_crash_on_valid_file(self, doc_strict):
        assert isinstance(doc_strict, Document)


# business-plan-90p-19tbl-7img.hwpx


class TestBusinessPlanDocument:
    """Known counts: 90 paragraphs, 19 tables, 7 images."""

    @pytest.fixture(scope="class")
    def doc(self):
        return _open(BUSINESS)

    @pytest.fixture(scope="class")
    def doc_strict(self):
        return _open(BUSINESS, strict=True)

    def test_returns_document(self, doc):
        assert isinstance(doc, Document)

    def test_paragraph_count(self, doc):
        assert len(doc.paragraphs) == 90

    def test_table_count(self, doc):
        assert len(doc.tables) == 19

    def test_image_count(self, doc):
        assert len(doc.images) == 7

    def test_images_are_imagerefs(self, doc):
        for img in doc.images:
            assert isinstance(img, ImageRef)

    def test_tables_have_cells(self, doc):
        for table in doc.tables:
            for row in table.rows:
                assert len(row.cells) > 0

    def test_body_order_is_sequential(self, doc):
        assert_block_indices_sequential(doc)

    def test_to_json_body_length(self, doc):
        data = json.loads(to_json(doc))
        assert len(data["body"]) == len(doc.blocks)

    def test_to_json_types(self, doc):
        data = json.loads(to_json(doc))
        type_values = {item["type"] for item in data["body"]}
        assert type_values <= {"paragraph", "table", "image"}

    def test_to_markdown_no_exception(self, doc):
        md = doc.to_markdown()
        assert isinstance(md, str)

    def test_to_text_no_exception(self, doc):
        text = doc.to_text()
        assert isinstance(text, str)

    def test_paragraph_styles_are_valid_enum(self, doc):
        for para in doc.paragraphs:
            assert isinstance(para.style, ParagraphStyle)

    def test_metadata_fields(self, doc):
        m = doc.metadata
        assert m.title is not None or m.author is not None

    def test_strict_mode_valid_file(self, doc_strict):
        assert len(doc_strict.paragraphs) == 90


# error handling


class TestErrorHandling:
    def test_corrupted_zip_raises(self, tmp_path):
        bad = tmp_path / "bad.hwpx"
        bad.write_bytes(b"not a zip file at all")
        with pytest.raises(CorruptedFileError):
            openhanji.open(bad)

    def test_empty_zip_produces_empty_document(self, tmp_path):
        empty = tmp_path / "empty.hwpx"
        with zipfile.ZipFile(empty, "w"):
            pass
        doc = openhanji.open(empty)
        assert isinstance(doc, Document)
        assert len(doc.blocks) == 0

    def test_zip_without_section_produces_empty_body(self, tmp_path):
        path = tmp_path / "nosection.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr(
                "content.hpf",
                "<package><metadata><title>T</title></metadata></package>",
            )
        doc = openhanji.open(path)
        assert len(doc.blocks) == 0

    def test_malformed_xml_section_skipped(self, tmp_path):
        path = tmp_path / "badxml.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("content.hpf", "<package/>")
            zf.writestr("Contents/section0.xml", "<<not valid xml>>")
        doc = openhanji.open(path)
        assert isinstance(doc, Document)

    def test_malformed_xml_section_strict_raises(self, tmp_path):
        path = tmp_path / "badxml_strict.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("content.hpf", "<package/>")
            zf.writestr("Contents/section0.xml", "<<not valid xml>>")
        with pytest.raises(CorruptedFileError):
            openhanji.open(path, strict=True)


    def test_text_box_gso_text_extracted(self, tmp_path):
        section_xml = sec(
            "<hp:p><hp:run>"
            "<hp:gso>"
            "<hp:p><hp:run><hp:t>텍스트 박스 내용</hp:t></hp:run></hp:p>"
            "</hp:gso>"
            "</hp:run></hp:p>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "gso.hwpx", section_xml))
        assert any("텍스트 박스 내용" in p.text for p in doc.paragraphs)

    def test_footnote_inlined(self, tmp_path):
        section_xml = sec(
            "<hp:p><hp:run><hp:t>본문 텍스트</hp:t></hp:run>"
            "<hp:footnote><hp:p><hp:run><hp:t>각주 내용</hp:t></hp:run></hp:p>"
            "</hp:footnote>"
            "</hp:p>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "fn.hwpx", section_xml))
        assert len(doc.paragraphs) == 1
        assert "[footnote:" in doc.paragraphs[0].text
        assert "각주 내용" in doc.paragraphs[0].text

    def test_endnote_inlined(self, tmp_path):
        section_xml = sec(
            "<hp:p><hp:run><hp:t>본문</hp:t></hp:run>"
            "<hp:endnote><hp:p><hp:run><hp:t>미주 내용</hp:t></hp:run></hp:p>"
            "</hp:endnote>"
            "</hp:p>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "en.hwpx", section_xml))
        assert "[endnote:" in doc.paragraphs[0].text
        assert "미주 내용" in doc.paragraphs[0].text

    def test_equation_placeholder_extracted(self, tmp_path):
        section_xml = sec(
            "<hp:p><hp:run><hp:t>수식: </hp:t>"
            "<hp:equation><hp:t>E=mc^2</hp:t></hp:equation>"
            "</hp:run></hp:p>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "eq.hwpx", section_xml))
        assert len(doc.paragraphs) == 1
        assert "[수식" in doc.paragraphs[0].text

    def test_nested_table_keeps_structured_blocks_and_recursive_text(self, tmp_path):
        section_xml = sec(
            "<ht:tbl>"
            "<ht:tr>"
            "<ht:tc>"
            "<hp:p><hp:run><hp:t>외부 셀</hp:t></hp:run></hp:p>"
            "<ht:tbl><ht:tr><ht:tc>"
            "<hp:p><hp:run><hp:t>내부 셀</hp:t></hp:run></hp:p>"
            "</ht:tc></ht:tr></ht:tbl>"
            "</ht:tc>"
            "</ht:tr>"
            "</ht:tbl>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "nested.hwpx", section_xml))
        assert len(doc.tables) >= 1
        outer_cell = doc.tables[0].rows[0].cells[0]
        assert [type(block).__name__ for block in outer_cell.blocks] == [
            "Paragraph",
            "Table",
        ]
        assert outer_cell.paragraphs[0].text == "외부 셀"
        assert len(outer_cell.tables) == 1
        assert outer_cell.tables[0].rows[0].cells[0].text == "내부 셀"
        assert outer_cell.text == "외부 셀\n내부 셀"
        assert "외부 셀\n내부 셀" in doc.to_text()

    def test_nested_table_only_document_renders_and_does_not_warn(
        self, tmp_path, caplog
    ):
        section_xml = sec(
            "<ht:tbl>"
            "<ht:tr>"
            "<ht:tc>"
            "<ht:tbl><ht:tr><ht:tc>"
            "<hp:p><hp:run><hp:t>내부 셀</hp:t></hp:run></hp:p>"
            "</ht:tc></ht:tr></ht:tbl>"
            "</ht:tc>"
            "</ht:tr>"
            "</ht:tbl>"
        )
        with caplog.at_level(logging.WARNING, logger="openhanji.parsers.hwpx"):
            doc = openhanji.open(make_hwpx(tmp_path, "nested_only.hwpx", section_xml))
        assert "내부 셀" in doc.to_text()
        assert "내부 셀" in doc.to_markdown()
        assert not any(
            "no text was extracted from paragraphs or table cells" in record.message
            for record in caplog.records
        )

    def test_inline_table_splits_paragraph_and_preserves_order(self, tmp_path):
        section_xml = sec(
            "<hp:p><hp:run><hp:t>앞</hp:t>"
            "<ht:tbl><ht:tr><ht:tc>"
            "<hp:p><hp:run><hp:t>표</hp:t></hp:run></hp:p>"
            "</ht:tc></ht:tr></ht:tbl>"
            "<hp:t>뒤</hp:t></hp:run></hp:p>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "mixed.hwpx", section_xml))
        assert [type(item).__name__ for item in doc.blocks] == [
            "Paragraph",
            "Table",
            "Paragraph",
        ]
        assert [para.text for para in doc.paragraphs] == ["앞", "뒤"]
        markdown = doc.to_markdown()
        assert markdown.index("앞") < markdown.index("| 표 |")
        assert markdown.index("| 표 |") < markdown.index("뒤")

    def test_equation_in_cell_survives_recursive_text_and_renderers(self, tmp_path):
        section_xml = sec(
            "<ht:tbl><ht:tr><ht:tc>"
            "<hp:p><hp:run>"
            "<hp:equation><hp:t>E=mc^2</hp:t></hp:equation>"
            "</hp:run></hp:p>"
            "</ht:tc></ht:tr></ht:tbl>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "cell_eq.hwpx", section_xml))
        cell = doc.tables[0].rows[0].cells[0]
        assert cell.text == "[수식: E=mc^2]"
        assert "[수식: E=mc^2]" in doc.to_text()
        assert "[수식: E=mc^2]" in doc.to_markdown()

    def test_simple_table_markdown_stays_gfm(self, tmp_path):
        section_xml = sec(
            "<ht:tbl>"
            "<ht:tr><ht:tc><hp:p><hp:run><hp:t>A</hp:t></hp:run></hp:p></ht:tc>"
            "<ht:tc><hp:p><hp:run><hp:t>B</hp:t></hp:run></hp:p></ht:tc></ht:tr>"
            "<ht:tr><ht:tc><hp:p><hp:run><hp:t>C</hp:t></hp:run></hp:p></ht:tc>"
            "<ht:tc><hp:p><hp:run><hp:t>D</hp:t></hp:run></hp:p></ht:tc></ht:tr>"
            "</ht:tbl>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "simple_md.hwpx", section_xml))
        markdown = doc.to_markdown()
        assert "| A | B |" in markdown
        assert "<table>" not in markdown

    def test_complex_table_markdown_uses_html_and_preserves_spans(self, tmp_path):
        section_xml = sec(
            "<ht:tbl>"
            "<ht:tr>"
            '<ht:tc><ht:cellSpan colSpan="2" rowSpan="1"/>'
            "<hp:p><hp:run><hp:t>헤더</hp:t></hp:run></hp:p>"
            "</ht:tc>"
            "</ht:tr>"
            "<ht:tr>"
            "<ht:tc><hp:p><hp:run><hp:t>왼쪽</hp:t></hp:run></hp:p></ht:tc>"
            "<ht:tc><hp:p><hp:run><hp:t>오른쪽</hp:t></hp:run></hp:p></ht:tc>"
            "</ht:tr>"
            "</ht:tbl>"
        )
        doc = openhanji.open(make_hwpx(tmp_path, "complex_md.hwpx", section_xml))
        markdown = doc.to_markdown()
        assert "<table>" in markdown
        assert 'colspan="2"' in markdown
        assert "헤더" in markdown

    def test_bindata_case_insensitive(self, tmp_path):
        png_bytes = (
            pathlib.Path(__file__).parent.parent
            / "test_files"
            / "png"
            / "inline-rgb-1x1.png"
        ).read_bytes()
        section_xml = sec(
            "<hp:p><hp:run>"
            '<hp:pic caption="img"><hp:img binaryItemIDRef="1"/>'
            '<hp:sz width="10" height="10"/></hp:pic>'
            "</hp:run></hp:p>"
        )
        path = tmp_path / "bincase.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("Contents/header.xml", "<hh:head/>")
            zf.writestr("Contents/section0.xml", section_xml)
            zf.writestr("bindata/image1.png", png_bytes)  # lowercase prefix
        doc = openhanji.open(path, with_images=True)
        assert doc.images[0].data == png_bytes

    def test_bindata_named_reference_resolves(self, tmp_path):
        png_bytes = (
            pathlib.Path(__file__).parent.parent
            / "test_files"
            / "png"
            / "inline-rgb-1x1.png"
        ).read_bytes()
        section_xml = sec(
            "<hp:p><hp:run>"
            '<hp:pic caption="img"><hp:img binaryItemIDRef="image1"/>'
            '<hp:sz width="10" height="10"/></hp:pic>'
            "</hp:run></hp:p>"
        )
        path = tmp_path / "binname.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("Contents/header.xml", "<hh:head/>")
            zf.writestr("Contents/section0.xml", section_xml)
            zf.writestr("BinData/image1.png", png_bytes)
        doc = openhanji.open(path, with_images=True)
        assert doc.images[0].data == png_bytes

    def test_spine_order_overrides_filename_sort(self, tmp_path):
        path = tmp_path / "spine.hwpx"
        section0 = sec("<hp:p><hp:run><hp:t>zero</hp:t></hp:run></hp:p>")
        section1 = sec("<hp:p><hp:run><hp:t>one</hp:t></hp:run></hp:p>")
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<opf:package xmlns:opf="http://www.idpf.org/2007/opf">'
            "<opf:manifest>"
            '<opf:item id="sec0" href="section0.xml"/>'
            '<opf:item id="sec1" href="section1.xml"/>'
            "</opf:manifest>"
            "<opf:spine>"
            '<opf:itemref idref="sec1"/>'
            '<opf:itemref idref="sec0"/>'
            "</opf:spine>"
            "</opf:package>"
        )
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("Contents/header.xml", "<hh:head/>")
            zf.writestr("Contents/content.hpf", content)
            zf.writestr("Contents/section0.xml", section0)
            zf.writestr("Contents/section1.xml", section1)
        doc = openhanji.open(path)
        assert [para.text for para in doc.paragraphs] == ["one", "zero"]

    def test_ref_list_font_and_paragraph_resolution(self, tmp_path):
        path = tmp_path / "style.hwpx"
        header = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
            'version="1.5" secCnt="1">'
            '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" '
            'tbl="1" equation="1"/>'
            "<hh:refList>"
            '<hh:fontfaces itemCnt="2">'
            '<hh:fontface lang="HANGUL" fontCnt="2">'
            '<hh:font id="0" face="함초롬돋움"/>'
            '<hh:font id="1" face="함초롬바탕"/>'
            "</hh:fontface>"
            "</hh:fontfaces>"
            '<hh:charProperties itemCnt="1">'
            '<hh:charPr id="7" textColor="#6182D6" height="1200">'
            '<hh:fontRef hangul="1" latin="0"/>'
            "</hh:charPr>"
            "</hh:charProperties>"
            '<hh:paraProperties itemCnt="1">'
            '<hh:paraPr id="20"><hh:align horizontal="CENTER"/></hh:paraPr>'
            "</hh:paraProperties>"
            '<hh:styles itemCnt="1">'
            '<hh:style id="3" name="Heading 1"/>'
            "</hh:styles>"
            "</hh:refList>"
            "</hh:head>"
        )
        section = sec(
            '<hp:p paraPrIDRef="20" styleIDRef="3">'
            '<hp:run charPrIDRef="7"><hp:t>제목</hp:t></hp:run>'
            "</hp:p>"
        )
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<opf:package xmlns:opf="http://www.idpf.org/2007/opf">'
            '<opf:manifest><opf:item id="sec0" href="section0.xml"/></opf:manifest>'
            '<opf:spine><opf:itemref idref="sec0"/></opf:spine>'
            "</opf:package>"
        )
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("Contents/content.hpf", content)
            zf.writestr("Contents/header.xml", header)
            zf.writestr("Contents/section0.xml", section)
        doc = openhanji.open(path)
        para = doc.paragraphs[0]
        assert para.style == ParagraphStyle.HEADING1
        assert para.align == "CENTER"
        assert para.style_name == "Heading 1"
        assert para.runs[0].font_face == "함초롬바탕"
        assert para.runs[0].font_size == 12.0
        assert para.runs[0].color == "#6182D6"

    def test_image_binary_extraction(self, tmp_path):
        png_bytes = (
            pathlib.Path(__file__).parent.parent
            / "test_files"
            / "png"
            / "inline-rgb-1x1.png"
        ).read_bytes()
        section_xml = sec(
            "<hp:p><hp:run>"
            '<hp:pic caption="Test Image">'
            '<hp:img binaryItemIDRef="1"/>'
            '<hp:sz width="400" height="150"/>'
            "</hp:pic>"
            "</hp:run></hp:p>"
        )
        path = tmp_path / "imgtest.hwpx"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("Contents/header.xml", "<hh:head/>")
            zf.writestr("Contents/section0.xml", section_xml)
            zf.writestr("BinData/image1.png", png_bytes)
        doc = openhanji.open(path, with_images=True)
        assert len(doc.images) == 1
        img = doc.images[0]
        assert img.data == png_bytes
        assert img.format == "png"
        assert img.caption == "Test Image"
        assert img.width == 400
        assert img.height == 150
