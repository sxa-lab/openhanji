"""Support types, constants, and pure helpers for the HWPX parser.

These are split out of `hwpx.py` to keep the main parser file focused on
the walker/state machine. Anything stateless and reusable across parser
methods belongs here; anything that touches `self` stays in `HwpxParser`.
"""

from __future__ import annotations

import posixpath
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from openhanji.document import ParagraphStyle


@dataclass
class CharShape:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_size: float | None = None
    color: str | None = None
    font_face: str | None = None        #Hangul font face
    font_face_latin: str | None = None  #Latin font face


@dataclass
class ParaShape:
    outline_level: str = ""
    list_kind: str = ""   # "ordered" | "unordered" | ""
    align: str = ""       # "left" | "center" | "right" | "justify" | ""


_BULLET_NUM_FORMATS = frozenset({"BULLET", "DISC", "CIRCLE", "SQUARE", "NONE"})


@dataclass
class HeaderIndex:
    font_faces: dict[str, dict[str, str]] = field(default_factory=dict)
    char_shapes: dict[str, CharShape] = field(default_factory=dict)
    para_shapes: dict[str, ParaShape] = field(default_factory=dict)
    styles: dict[str, str] = field(default_factory=dict)
    #numbering id -> "ordered" | "unordered"
    numbering: dict[str, str] = field(default_factory=dict)


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _extract_hyperlink_url(field_begin: ET.Element) -> str | None:
    """Return the URL from a fieldBegin[type=HYPERLINK] element, or None."""
    for child in field_begin:
        if _strip_ns(child.tag) == "parameters":
            for param in child:
                if (
                    _strip_ns(param.tag) == "stringParam"
                    and param.get("name") == "Path"
                    and param.text
                ):
                    return param.text.strip()
    return None


def _resolve_part(base_path: str, href: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(base_path), href))


_HEADING_STYLES = {
    "1": ParagraphStyle.HEADING1,
    "2": ParagraphStyle.HEADING2,
    "3": ParagraphStyle.HEADING3,
    "4": ParagraphStyle.HEADING4,
    "5": ParagraphStyle.HEADING5,
    "6": ParagraphStyle.HEADING6,
}

#Font faces used as heading/title fonts in Korean documents.
#These never appear on body-text runs in the corpus.
_HEADING_FONT_FACES = frozenset({
    "HY헤드라인M", "HY헤드라인B",
    "HY울릉도M", "HY견고딕",
    "바탕",
})

#Fonts that are always body text regardless of size or bold.
#Short-circuit the heuristic before the size thresholds are checked.
_BODY_FONT_FACES = frozenset({
    "맑은 고딕",
})

_SPACE_TAGS = frozenset({"tab", "nbSpace", "fwSpace"})

_SKIP_TAGS = frozenset({
    "linesegarray", "lineseg", "charShape", "paraShape",
    "secPr", "borderFill", "fillBrush", "trackChange",
    "fieldBegin", "fieldEnd", "pageNum",
    "cellAddr", "cellSpan", "cellSz", "cellMargin",
    "sz", "pos", "outMargin", "inMargin", "rotationInfo",
    "orgSz", "curSz", "flip", "offset", "stringParam",
    "head",
})

_INLINE_OBJECT_TAGS = frozenset({"tbl", "pic", "img", "image"})
_TEXT_BOX_TAGS = frozenset({"gso", "drawText"})

#Tags whose text content is extracted with a label prefix.
_NOTE_TAGS = frozenset({"footnote", "endnote"})
_EQUATION_TAGS = frozenset({"equation", "equationObject", "ole"})
