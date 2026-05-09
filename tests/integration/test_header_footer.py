"""Integration tests for header and footer extraction from HWPX ctrl elements."""

import json
import pathlib

import openhanji
from openhanji.converters.json import to_json
from openhanji.models.document import Paragraph

TEST_FILES = pathlib.Path(__file__).parent.parent / "test_files"
HF_FIXTURE = TEST_FILES / "hwpx" / "sxa_header-footer-ctrl.hwpx"
BASIC_FIXTURE = TEST_FILES / "hwpx" / "sxa_owpml-structure-coverage.hwpx"


class DescribeHeaderFooterExtraction:
    def it_extracts_header_paragraphs(self):
        doc = openhanji.open(HF_FIXTURE)
        assert len(doc.headers) == 1
        assert doc.headers[0].text == "OpenHanji Test Header"

    def it_extracts_footer_paragraphs(self):
        doc = openhanji.open(HF_FIXTURE)
        assert len(doc.footers) == 1
        assert doc.footers[0].text == "Page 1"

    def it_returns_paragraph_instances(self):
        doc = openhanji.open(HF_FIXTURE)
        assert all(isinstance(p, Paragraph) for p in doc.headers)
        assert all(isinstance(p, Paragraph) for p in doc.footers)

    def it_does_not_include_hf_content_in_body(self):
        doc = openhanji.open(HF_FIXTURE)
        body_texts = {p.text for p in doc.paragraphs}
        assert "OpenHanji Test Header" not in body_texts
        assert "Page 1" not in body_texts

    def it_preserves_body_paragraphs(self):
        doc = openhanji.open(HF_FIXTURE)
        assert len(doc.paragraphs) == 2
        assert doc.paragraphs[0].text == "Body paragraph one."
        assert doc.paragraphs[1].text == "Body paragraph two."

    def it_returns_empty_lists_when_no_hf_present(self):
        doc = openhanji.open(BASIC_FIXTURE)
        assert doc.headers == []
        assert doc.footers == []


class DescribeJsonOutput:
    def it_includes_headers_key_when_present(self):
        doc = openhanji.open(HF_FIXTURE)
        data = json.loads(to_json(doc))
        assert "headers" in data
        assert len(data["headers"]) == 1
        assert data["headers"][0]["text"] == "OpenHanji Test Header"

    def it_includes_footers_key_when_present(self):
        doc = openhanji.open(HF_FIXTURE)
        data = json.loads(to_json(doc))
        assert "footers" in data
        assert data["footers"][0]["text"] == "Page 1"

    def it_omits_headers_key_when_absent(self):
        doc = openhanji.open(BASIC_FIXTURE)
        data = json.loads(to_json(doc))
        assert "headers" not in data
        assert "footers" not in data


class DescribeMarkdownOutput:
    def it_emits_header_comment_before_body(self):
        doc = openhanji.open(HF_FIXTURE)
        md = doc.to_markdown()
        assert "<!-- header: OpenHanji Test Header -->" in md
        header_pos = md.index("<!-- header:")
        body_pos = md.index("Body paragraph one.")
        assert header_pos < body_pos

    def it_emits_footer_comment_after_body(self):
        doc = openhanji.open(HF_FIXTURE)
        md = doc.to_markdown()
        assert "<!-- footer: Page 1 -->" in md
        body_pos = md.index("Body paragraph two.")
        footer_pos = md.index("<!-- footer:")
        assert footer_pos > body_pos

    def it_omits_hf_comments_when_absent(self):
        doc = openhanji.open(BASIC_FIXTURE)
        md = doc.to_markdown()
        assert "<!-- header:" not in md
        assert "<!-- footer:" not in md


class DescribeTextOutput:
    def it_emits_header_label_before_body(self):
        doc = openhanji.open(HF_FIXTURE)
        text = doc.to_text()
        lines = text.splitlines()
        assert lines[0] == "[header: OpenHanji Test Header]"

    def it_emits_footer_label_after_body(self):
        doc = openhanji.open(HF_FIXTURE)
        text = doc.to_text()
        lines = text.splitlines()
        assert lines[-1] == "[footer: Page 1]"

    def it_omits_hf_labels_when_absent(self):
        doc = openhanji.open(BASIC_FIXTURE)
        text = doc.to_text()
        assert "[header:" not in text
        assert "[footer:" not in text
