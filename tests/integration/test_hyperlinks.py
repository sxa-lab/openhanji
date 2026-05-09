"""Integration tests for HYPERLINK field extraction."""

import json
import pathlib

import openhanji
from openhanji.converters.json import to_json

TEST_FILES = pathlib.Path(__file__).parent.parent / "test_files"
FIXTURE = TEST_FILES / "hwpx" / "sxa_hyperlink-field.hwpx"
BASIC = TEST_FILES / "hwpx" / "sxa_owpml-structure-coverage.hwpx"


class DescribeHyperlinkExtraction:
    def it_attaches_href_to_linked_runs(self):
        doc = openhanji.open(FIXTURE)
        linked = [r for p in doc.paragraphs for r in p.runs if r.href]
        assert len(linked) == 1
        assert linked[0].text == "the docs"
        assert linked[0].href == "https://openhanji.readthedocs.io"

    def it_leaves_surrounding_runs_without_href(self):
        doc = openhanji.open(FIXTURE)
        para = doc.paragraphs[0]
        unlinked = [r for r in para.runs if not r.href]
        assert any(r.text == "Visit " for r in unlinked)
        assert any(r.text == " for details." for r in unlinked)

    def it_preserves_full_paragraph_text(self):
        doc = openhanji.open(FIXTURE)
        assert doc.paragraphs[0].text == "Visit the docs for details."

    def it_returns_no_hrefs_when_no_hyperlinks_present(self):
        doc = openhanji.open(BASIC)
        linked = [r for p in doc.paragraphs for r in p.runs if r.href]
        assert linked == []


class DescribeMarkdownOutput:
    def it_renders_link_syntax(self):
        doc = openhanji.open(FIXTURE)
        md = doc.to_markdown()
        assert "[the docs](https://openhanji.readthedocs.io)" in md

    def it_preserves_surrounding_text(self):
        doc = openhanji.open(FIXTURE)
        md = doc.to_markdown()
        assert "Visit" in md
        assert "for details." in md

    def it_does_not_emit_link_syntax_for_plain_paragraphs(self):
        doc = openhanji.open(FIXTURE)
        md = doc.to_markdown()
        assert "Plain paragraph with no links." in md
        assert md.count("](") == 1


class DescribeJsonOutput:
    def it_includes_href_on_linked_runs(self):
        doc = openhanji.open(FIXTURE)
        data = json.loads(to_json(doc))
        runs = [r for b in data["body"] if b["type"] == "paragraph" for r in b["runs"]]
        linked = [r for r in runs if "href" in r]
        assert len(linked) == 1
        assert linked[0]["href"] == "https://openhanji.readthedocs.io"

    def it_omits_href_key_from_unlinked_runs(self):
        doc = openhanji.open(FIXTURE)
        data = json.loads(to_json(doc))
        runs = [r for b in data["body"] if b["type"] == "paragraph" for r in b["runs"]]
        unlinked = [r for r in runs if "href" not in r]
        assert len(unlinked) > 0
