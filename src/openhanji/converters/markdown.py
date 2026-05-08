"""Converts a Document to GitHub-flavoured Markdown."""

from __future__ import annotations

import base64
import html

from openhanji.document import Document, ImageRef, Paragraph, ParagraphStyle, Run, Table

_HEADING_PREFIX = {
    ParagraphStyle.HEADING1: "#",
    ParagraphStyle.HEADING2: "##",
    ParagraphStyle.HEADING3: "###",
    ParagraphStyle.HEADING4: "####",
    ParagraphStyle.HEADING5: "#####",
    ParagraphStyle.HEADING6: "######",
}


def to_markdown(doc: Document) -> str:
    parts: list[str] = []
    if doc.headers:
        header_text = " | ".join(
            b.text for b in doc.headers if isinstance(b, Paragraph) and b.text
        )
        if header_text:
            parts.append(f"<!-- header: {header_text} -->")
    for item in doc.blocks:
        if isinstance(item, Paragraph):
            parts.append(_paragraph_to_md(item))
        elif isinstance(item, Table):
            parts.append(_table_to_md(item))
        elif isinstance(item, ImageRef):
            parts.append(_image_to_md(item))
    if doc.footers:
        footer_text = " | ".join(
            b.text for b in doc.footers if isinstance(b, Paragraph) and b.text
        )
        if footer_text:
            parts.append(f"<!-- footer: {footer_text} -->")
    return "\n\n".join(p for p in parts if p)


def _paragraph_to_md(para: Paragraph) -> str:
    prefix = _HEADING_PREFIX.get(para.style)

    if para.runs and any(r.bold or r.italic or r.underline or r.href
                         for r in para.runs):
        text = "".join(_run_to_md(r) for r in para.runs).strip()
    else:
        text = para.text

    if prefix:
        return f"{prefix} {text}"
    if para.style == ParagraphStyle.LIST_UNORDERED:
        return f"{'  ' * para.level}- {text}"
    if para.style == ParagraphStyle.LIST_ORDERED:
        return f"{'  ' * para.level}1. {text}"
    return text


def _run_to_md(run: Run) -> str:
    text = run.text
    if run.bold and run.italic:
        text = f"***{text}***"
    elif run.bold:
        text = f"**{text}**"
    elif run.italic:
        text = f"_{text}_"
    if run.href:
        return f"[{text}]({run.href})"
    return text


def _table_to_md(table: Table) -> str:
    if _is_simple_table(table):
        return _simple_table_to_md(table)
    return _complex_table_to_html(table)


def _is_simple_table(table: Table) -> bool:
    if not table.rows or not table.rows[0].cells:
        return False
    for row in table.rows:
        for cell in row.cells:
            if cell.col_span != 1 or cell.row_span != 1:
                return False
            if len(cell.blocks) != 1:
                return False
            only = cell.blocks[0]
            if not isinstance(only, Paragraph):
                return False
            if "\n" in only.text:
                return False
    return True


def _simple_table_to_md(table: Table) -> str:
    lines: list[str] = []
    if table.caption:
        lines.append(f"*{table.caption}*\n")

    header_cells = [_plain_cell_md(cell.text) for cell in table.rows[0].cells]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

    for row in table.rows[1:]:
        cells = [_plain_cell_md(cell.text) for cell in row.cells]
        while len(cells) < len(header_cells):
            cells.append("")
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _plain_cell_md(text: str) -> str:
    return text.replace("\n", " ").replace("|", "\\|")


def _complex_table_to_html(table: Table) -> str:
    lines = ["<table>"]
    if table.caption:
        lines.append(f"<caption>{html.escape(table.caption)}</caption>")
    for row_index, row in enumerate(table.rows):
        lines.append("<tr>")
        cell_tag = "th" if row_index == 0 else "td"
        for cell in row.cells:
            attrs: list[str] = []
            if cell.col_span > 1:
                attrs.append(f' colspan="{cell.col_span}"')
            if cell.row_span > 1:
                attrs.append(f' rowspan="{cell.row_span}"')
            inner = _blocks_to_html(cell.blocks) or html.escape(cell.text)
            lines.append(f"<{cell_tag}{''.join(attrs)}>{inner}</{cell_tag}>")
        lines.append("</tr>")
    lines.append("</table>")
    return "\n".join(lines)


def _blocks_to_html(blocks: list[Paragraph | Table | ImageRef]) -> str:
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, Paragraph):
            parts.append(_paragraph_to_html(block))
        elif isinstance(block, Table):
            parts.append(_complex_table_to_html(block))
        elif isinstance(block, ImageRef):
            parts.append(_image_to_html(block))
    return "".join(parts)


def _paragraph_to_html(para: Paragraph) -> str:
    if para.runs:
        content = "".join(_run_to_html(run) for run in para.runs)
    else:
        content = html.escape(para.text)
    content = content.replace("\n", "<br />")
    return f"<p>{content}</p>"


def _run_to_html(run: Run) -> str:
    text = html.escape(run.text).replace("\n", "<br />")
    if run.underline:
        text = f"<u>{text}</u>"
    if run.bold:
        text = f"<strong>{text}</strong>"
    if run.italic:
        text = f"<em>{text}</em>"
    if run.href:
        text = f'<a href="{html.escape(run.href)}">{text}</a>'
    return text


def _image_to_md(image: ImageRef) -> str:
    caption = image.caption or f"image_{image.image_seq}"
    if image.data and image.format:
        mime = f"image/{image.format}"
        b64 = base64.b64encode(image.data).decode()
        return f"![{caption}](data:{mime};base64,{b64})"
    return f"![{caption}](image_{image.image_seq})"


def _image_to_html(image: ImageRef) -> str:
    caption = image.caption or f"image_{image.image_seq}"
    alt = html.escape(caption)
    if image.data and image.format:
        mime = f"image/{image.format}"
        b64 = base64.b64encode(image.data).decode()
        return f'<img alt="{alt}" src="data:{mime};base64,{b64}" />'
    return f'<img alt="{alt}" src="image_{image.image_seq}" />'
