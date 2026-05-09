"""Converts a Document to plain text."""

from __future__ import annotations

from openhanji.models.document import Document, ImageRef, Paragraph, Table


def to_text(doc: Document) -> str:
    lines: list[str] = []
    if doc.headers:
        header_text = " | ".join(
            b.text for b in doc.headers if isinstance(b, Paragraph) and b.text
        )
        if header_text:
            lines.append(f"[header: {header_text}]")
    lines.extend(_blocks_to_lines(doc.blocks))
    if doc.footers:
        footer_text = " | ".join(
            b.text for b in doc.footers if isinstance(b, Paragraph) and b.text
        )
        if footer_text:
            lines.append(f"[footer: {footer_text}]")
    return "\n".join(lines)


def _blocks_to_lines(blocks: list[Paragraph | Table | ImageRef]) -> list[str]:
    lines: list[str] = []
    for block in blocks:
        if isinstance(block, Paragraph):
            if block.text:
                lines.append(block.text)
        elif isinstance(block, Table):
            lines.extend(_table_to_lines(block))
        elif isinstance(block, ImageRef) and block.caption:
            lines.append(f"[Image: {block.caption}]")
    return lines


def _table_to_lines(table: Table) -> list[str]:
    lines: list[str] = []
    for row in table.rows:
        row_text = "\t".join(cell.text for cell in row.cells)
        if row_text:
            lines.append(row_text)
    return lines
