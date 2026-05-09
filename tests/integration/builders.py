"""Shared HWPX builder helpers and assertion helpers for integration tests."""

from __future__ import annotations

import json
import pathlib
import zipfile


def sec(body: str) -> str:
    """Wrap body XML in a minimal hs:sec element with all required namespaces."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
        ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
        ' xmlns:ht="http://www.hancom.co.kr/hwpml/2011/table">' + body + "</hs:sec>"
    )


def make_hwpx(
    tmp_path: pathlib.Path,
    name: str,
    section_xml: str,
    header_xml: str = "<hh:head/>",
) -> pathlib.Path:
    """Build a minimal HWPX zip with the given section XML and return its path."""
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", header_xml)
        zf.writestr("Contents/section0.xml", section_xml)
    return path


def make_charpr_hwpx(
    tmp_path: pathlib.Path,
    font_face: str,
    font_size_hwpunit: int,
    bold: bool,
    text: str,
    outline_level: str = "",
    name: str = "para.hwpx",
) -> pathlib.Path:
    """Build a minimal HWPX whose single paragraph uses the given charPr.

    font_size_hwpunit is in 1/100 pt units (e.g. 2000 = 20pt).
    outline_level, if given, sets outlineLevel attribute on paraPr.
    """
    bold_val = "1" if bold else "0"
    outline_attr = f' outlineLevel="{outline_level}"' if outline_level else ""
    header = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
        ' version="1.5" secCnt="1">'
        '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
        "<hh:refList>"
        '<hh:fontfaces itemCnt="1">'
        '<hh:fontface lang="HANGUL" fontCnt="1">'
        f'<hh:font id="0" face="{font_face}"/>'
        "</hh:fontface>"
        "</hh:fontfaces>"
        '<hh:charProperties itemCnt="1">'
        f'<hh:charPr id="0" height="{font_size_hwpunit}" bold="{bold_val}">'
        '<hh:fontRef hangul="0" latin="0"/>'
        "</hh:charPr>"
        "</hh:charProperties>"
        '<hh:paraProperties itemCnt="1">'
        f'<hh:paraPr id="0"{outline_attr}/>'
        "</hh:paraProperties>"
        '<hh:styles itemCnt="0"/>'
        "</hh:refList>"
        "</hh:head>"
    )
    section = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
        ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        '<hp:p paraPrIDRef="0">'
        '<hp:run charPrIDRef="0">'
        f"<hp:t>{text}</hp:t>"
        "</hp:run>"
        "</hp:p>"
        "</hs:sec>"
    )
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", header)
        zf.writestr("Contents/section0.xml", section)
    return path


# ---------------------------------------------------------------------------
# Shared assertion helpers — call these from real-document test files instead
# of repeating the same assertion logic in every file.
# ---------------------------------------------------------------------------


def assert_block_indices_sequential(doc) -> None:
    """Block .index values form an unbroken 0-based sequence."""
    indices = [b.index for b in doc.blocks]
    assert indices == list(range(len(indices)))


def assert_run_text_invariant(doc) -> None:
    """para.text == ''.join(r.text for r in para.runs) for every top-level paragraph."""
    for para in doc.paragraphs:
        if para.runs:
            assert para.text == "".join(r.text for r in para.runs)


def assert_run_text_invariant_cells(doc) -> None:
    """Same invariant holds for every paragraph inside every table cell."""
    from openhanji.models.document import Paragraph

    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for block in cell.blocks:
                    if isinstance(block, Paragraph) and block.runs:
                        assert block.text == "".join(r.text for r in block.runs)


def assert_to_markdown_non_empty(doc) -> None:
    assert doc.to_markdown().strip()


def assert_to_text_non_empty(doc) -> None:
    assert doc.to_text().strip()


def assert_strict_block_count_unchanged(fixture: pathlib.Path) -> None:
    """Opening with strict=True must yield the same block count as default."""
    import openhanji

    assert len(openhanji.open(fixture).blocks) == len(
        openhanji.open(fixture, strict=True).blocks
    )


def assert_to_json_body_matches_blocks(doc) -> None:
    """Flat JSON body length equals doc.blocks length."""
    from openhanji.converters.json import to_json

    data = json.loads(to_json(doc))
    assert len(data["body"]) == len(doc.blocks)


def assert_to_json_structured_sections_match(doc) -> None:
    """Sum of blocks across all structured sections equals doc.blocks length."""
    from openhanji.converters.json import to_json

    data = json.loads(to_json(doc, mode="structured"))
    total = sum(len(s["blocks"]) for s in data["sections"])
    assert total == len(doc.blocks)


def assert_none_mode_no_headings(fixture: pathlib.Path) -> None:
    """heading_detection='none' must produce zero HEADING* paragraphs."""
    import openhanji

    doc = openhanji.open(fixture, heading_detection="none")
    assert not any(p.style.value.startswith("HEADING") for p in doc.paragraphs)


def assert_to_json_block_types_valid(doc) -> None:
    """Every item in the flat JSON body must be paragraph, table, or image."""
    from openhanji.converters.json import to_json

    data = json.loads(to_json(doc))
    bad = [b for b in data["body"] if b["type"] not in {"paragraph", "table", "image"}]
    assert not bad


def assert_none_mode_block_count_unchanged(fixture: pathlib.Path) -> None:
    """heading_detection='none' must not add or remove blocks."""
    import openhanji

    assert len(openhanji.open(fixture).blocks) == len(
        openhanji.open(fixture, heading_detection="none").blocks
    )
