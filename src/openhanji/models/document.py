"""Document model: Section, Paragraph, Run, Table, Cell, ImageRef, Metadata."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ParagraphStyle(str, Enum):
    HEADING1 = "HEADING1"
    HEADING2 = "HEADING2"
    HEADING3 = "HEADING3"
    HEADING4 = "HEADING4"
    HEADING5 = "HEADING5"
    HEADING6 = "HEADING6"
    BODY = "BODY"
    LIST_UNORDERED = "LIST_UNORDERED"
    LIST_ORDERED = "LIST_ORDERED"


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_size: float | None = None  # points
    color: str | None = None  # hex e.g. "#FF0000"
    font_face: str | None = None  # resolved Hangul font face
    href: str | None = None  # set when run is inside a HYPERLINK field

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"text": self.text}
        if self.bold:
            d["bold"] = True
        if self.italic:
            d["italic"] = True
        if self.underline:
            d["underline"] = True
        if self.font_size is not None:
            d["font_size"] = self.font_size
        if self.color is not None:
            d["color"] = self.color
        if self.font_face is not None:
            d["font_face"] = self.font_face
        if self.href is not None:
            d["href"] = self.href
        return d


@dataclass
class Paragraph:
    text: str = ""
    style: ParagraphStyle = ParagraphStyle.BODY
    level: int = 0
    runs: list[Run] = field(default_factory=list)
    index: int = 0
    align: str | None = None
    style_name: str | None = None

    def __post_init__(self) -> None:
        if self.runs:
            joined = "".join(r.text for r in self.runs)
            if self.text != joined:
                raise ValueError(f"Paragraph.text {self.text!r} != run join {joined!r}")

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "type": "paragraph",
            "index": self.index,
            "style": self.style.value,
            "level": self.level,
            "text": self.text,
            "runs": [r.to_dict() for r in self.runs],
        }
        if self.align is not None:
            d["align"] = self.align
        if self.style_name is not None:
            d["style_name"] = self.style_name
        return d


@dataclass
class Cell:
    col_span: int = 1
    row_span: int = 1
    blocks: list[Paragraph | Table | ImageRef] = field(default_factory=list)

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [b for b in self.blocks if isinstance(b, Paragraph)]

    @property
    def tables(self) -> list[Table]:
        return [b for b in self.blocks if isinstance(b, Table)]

    @property
    def images(self) -> list[ImageRef]:
        return [b for b in self.blocks if isinstance(b, ImageRef)]

    @property
    def text(self) -> str:
        return _blocks_to_plain_text(self.blocks)

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "col_span": self.col_span,
            "row_span": self.row_span,
            "blocks": [b.to_dict() for b in self.blocks],
        }


@dataclass
class Row:
    cells: list[Cell] = field(default_factory=list)


@dataclass
class Table:
    rows: list[Row] = field(default_factory=list)
    caption: str | None = None
    index: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "table",
            "index": self.index,
            "caption": self.caption,
            "rows": [{"cells": [c.to_dict() for c in row.cells]} for row in self.rows],
        }


@dataclass
class ImageRef:
    index: int = 0
    image_seq: int = 0  # document-global counter for placeholder names
    caption: str | None = None
    width: int | None = None
    height: int | None = None
    data: bytes | None = None
    format: str | None = None  # e.g. "png", "jpg", "bmp"

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "image",
            "index": self.index,
            "caption": self.caption,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "data": base64.b64encode(self.data).decode() if self.data else None,
        }


@dataclass
class Section:
    blocks: list[Paragraph | Table | ImageRef] = field(default_factory=list)
    headers: list[Paragraph | Table | ImageRef] = field(default_factory=list)
    footers: list[Paragraph | Table | ImageRef] = field(default_factory=list)
    index: int = 0
    source_path: str | None = None  # e.g. "Contents/section0.xml"

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [b for b in self.blocks if isinstance(b, Paragraph)]

    @property
    def tables(self) -> list[Table]:
        return [b for b in self.blocks if isinstance(b, Table)]

    @property
    def images(self) -> list[ImageRef]:
        return [b for b in self.blocks if isinstance(b, ImageRef)]

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "index": self.index,
            "source_path": self.source_path,
            "blocks": [b.to_dict() for b in self.blocks],
        }
        if self.headers:
            d["headers"] = [b.to_dict() for b in self.headers]
        if self.footers:
            d["footers"] = [b.to_dict() for b in self.footers]
        return d


def _blocks_to_plain_text(blocks: list[Paragraph | Table | ImageRef]) -> str:
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, Paragraph):
            if block.text:
                parts.append(block.text)
        elif isinstance(block, Table):
            row_lines = [
                "\t".join(cell.text for cell in row.cells) for row in block.rows
            ]
            table_text = "\n".join(line for line in row_lines if line)
            if table_text:
                parts.append(table_text)
        elif isinstance(block, ImageRef) and block.caption:
            parts.append(f"[Image: {block.caption}]")
    return "\n".join(parts)


@dataclass
class Metadata:
    title: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    page_count: int | None = None
    subject: str | None = None
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "page_count": self.page_count,
            "subject": self.subject,
            "keywords": self.keywords,
        }


class Document:
    def __init__(
        self,
        metadata: Metadata | None = None,
        sections: list[Section] | None = None,
        body: list[Paragraph | Table | ImageRef] | None = None,
    ) -> None:
        self.metadata: Metadata = metadata or Metadata()
        if sections is not None:
            self.sections: list[Section] = sections
        elif body is not None:
            # Wrap a flat block list into a single anonymous section.
            self.sections = [Section(blocks=body)]
        else:
            self.sections = []

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [b for s in self.sections for b in s.blocks if isinstance(b, Paragraph)]

    @property
    def tables(self) -> list[Table]:
        return [b for s in self.sections for b in s.blocks if isinstance(b, Table)]

    @property
    def images(self) -> list[ImageRef]:
        return [b for s in self.sections for b in s.blocks if isinstance(b, ImageRef)]

    @property
    def headers(self) -> list[Paragraph | Table | ImageRef]:
        return [b for s in self.sections for b in s.headers]

    @property
    def footers(self) -> list[Paragraph | Table | ImageRef]:
        return [b for s in self.sections for b in s.footers]

    @property
    def blocks(self) -> list[Paragraph | Table | ImageRef]:
        """Flattened ordered list of all top-level blocks across all sections."""
        return [b for s in self.sections for b in s.blocks]

    def to_markdown(self) -> str:
        from openhanji.converters.markdown import to_markdown

        return to_markdown(self)

    def to_text(self) -> str:
        from openhanji.converters.text import to_text

        return to_text(self)

    def to_json(self, indent: int = 2, *, mode: str = "flat") -> str:
        from openhanji.converters.json import to_json

        return to_json(self, indent=indent, mode=mode)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        return (
            f"Document(title={self.metadata.title!r}, "
            f"sections={len(self.sections)}, "
            f"paragraphs={len(self.paragraphs)}, "
            f"tables={len(self.tables)})"
        )
