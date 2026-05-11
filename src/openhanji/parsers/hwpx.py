"""Parses HWPX files (ZIP + OWPML XML) into a Document."""

from __future__ import annotations

import logging
import pathlib
import re
import xml.etree.ElementTree as ET
import zipfile

from openhanji.exceptions import CorruptedFileError, UnknownRecordError
from openhanji.models.document import (
    Cell,
    Document,
    ImageRef,
    Paragraph,
    ParagraphStyle,
    Row,
    Run,
    Section,
    Table,
)
from openhanji.parsers.base import BaseParser
from openhanji.parsers.hwpx_index import (
    index_bindata,
    index_header,
    parse_metadata,
    parse_package,
    section_files,
)
from openhanji.parsers.hwpx_support import (
    _BODY_FONT_FACES,
    _EQUATION_TAGS,
    _HEADING_FONT_FACES,
    _HEADING_STYLES,
    _INLINE_OBJECT_TAGS,
    _NOTE_TAGS,
    _SKIP_TAGS,
    _SPACE_TAGS,
    _TEXT_BOX_TAGS,
    CharShape,
    HeaderIndex,
    ParaShape,
    _extract_hyperlink_url,
    _parse_int,
    _strip_ns,
)

__all__ = ["HwpxParser", "CharShape", "HeaderIndex", "ParaShape"]

logger = logging.getLogger(__name__)


class HwpxParser(BaseParser):
    def parse(self, path: pathlib.Path) -> Document:
        try:
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                metadata = parse_metadata(zf, names, strict=self.strict)
                sections = self._parse_body(zf, names)
                doc = Document(metadata=metadata, sections=sections)
                self._reindex_images(doc)
                return doc
        except zipfile.BadZipFile as exc:
            raise CorruptedFileError(f"Not a valid HWPX file: {path}") from exc
        except (CorruptedFileError, UnknownRecordError):
            raise
        except Exception as exc:
            raise CorruptedFileError(f"Failed to parse {path}: {exc}") from exc

    @staticmethod
    def _reindex_images(doc: Document) -> None:
        """Assign a document-global sequential index to every ImageRef.

        Local parsing assigns indices relative to the current block list, which
        means images in different cells or header/footer regions can all start
        at 0. This walk visits every ImageRef in section order and reassigns a
        monotonically increasing counter so that placeholder names like image_0,
        image_1, ... are unique across the whole document.
        """
        counter = 0

        def visit_blocks(blocks: list[Paragraph | Table | ImageRef]) -> None:
            nonlocal counter
            for block in blocks:
                if isinstance(block, ImageRef):
                    block.image_seq = counter
                    counter += 1
                elif isinstance(block, Table):
                    for row in block.rows:
                        for cell in row.cells:
                            visit_blocks(cell.blocks)

        for section in doc.sections:
            visit_blocks(section.headers)
            visit_blocks(section.blocks)
            visit_blocks(section.footers)

    def _parse_body(self, zf: zipfile.ZipFile, names: list[str]) -> list[Section]:
        package = parse_package(zf, names, strict=self.strict)
        bindata = index_bindata(zf, names, with_images=self.with_images)
        header_index = index_header(zf, names, strict=self.strict)

        section_paths = section_files(names, package)
        if not section_paths:
            logger.warning("No section files found in HWPX archive")
            return []

        sections: list[Section] = []
        body_index = 0
        for sec_idx, section_path in enumerate(section_paths):
            blocks: list[Paragraph | Table | ImageRef] = []
            headers: list[Paragraph | Table | ImageRef] = []
            footers: list[Paragraph | Table | ImageRef] = []
            try:
                with zf.open(section_path) as f:
                    section_xml = ET.parse(f).getroot()
                body_index = self._walk(
                    section_xml,
                    blocks,
                    body_index,
                    bindata,
                    header_index,
                    headers,
                    footers,
                )
            except ET.ParseError as exc:
                logger.warning("Could not parse %s: %s", section_path, exc)
                if self.strict:
                    raise CorruptedFileError(f"Parse error in {section_path}") from exc
            sections.append(
                Section(
                    blocks=blocks,
                    headers=headers,
                    footers=footers,
                    index=sec_idx,
                    source_path=section_path,
                )
            )

        all_blocks = [b for s in sections for b in s.blocks]
        if not self._has_text(all_blocks):
            logger.warning(
                "Document parsed, but no text was extracted from paragraphs "
                "or table cells."
            )

        return sections

    def _walk(
        self,
        elem: ET.Element,
        body: list[Paragraph | Table | ImageRef],
        index: int,
        bindata: dict[str, tuple[bytes, str]] | None = None,
        header_index: HeaderIndex | None = None,
        headers: list[Paragraph | Table | ImageRef] | None = None,
        footers: list[Paragraph | Table | ImageRef] | None = None,
    ) -> int:
        for child in elem:
            tag = _strip_ns(child.tag)

            if tag in _SKIP_TAGS:
                continue
            elif tag == "ctrl":
                index = self._walk(
                    child, body, index, bindata, header_index, headers, footers
                )
            elif tag == "header":
                self._parse_header_footer(
                    child, headers if headers is not None else [], bindata, header_index
                )
            elif tag == "footer":
                self._parse_header_footer(
                    child, footers if footers is not None else [], bindata, header_index
                )
            elif tag == "p":
                index = self._process_p(
                    child, body, index, bindata, header_index, headers, footers
                )
            elif tag == "tbl":
                table = self._parse_table(child, index, bindata, header_index)
                if table:
                    body.append(table)
                    index += 1
            elif tag in _INLINE_OBJECT_TAGS:
                image = self._parse_image(child, index, bindata)
                if image:
                    body.append(image)
                    index += 1
            else:
                if self.strict:
                    parent = _strip_ns(elem.tag)
                    raise UnknownRecordError(
                        f"Unrecognised block element <{tag}> inside <{parent}>"
                    )
                logger.warning(
                    "Unrecognised block element <%s> inside <%s>; descending",
                    tag,
                    _strip_ns(elem.tag),
                )
                index = self._walk(
                    child, body, index, bindata, header_index, headers, footers
                )

        return index

    def _parse_header_footer(
        self,
        elem: ET.Element,
        target: list[Paragraph | Table | ImageRef],
        bindata: dict[str, tuple[bytes, str]] | None = None,
        header_index: HeaderIndex | None = None,
    ) -> None:
        """Extract all blocks from a header or footer element's subList children."""
        for child in elem:
            tag = _strip_ns(child.tag)
            if tag == "subList":
                index = 0
                for sub_elem in child:
                    sub_tag = _strip_ns(sub_elem.tag)
                    if sub_tag == "p":
                        for block in self._parse_paragraph_blocks(
                            sub_elem, bindata, header_index
                        ):
                            if isinstance(block, Paragraph):
                                if block.text:
                                    block.index = index
                                    target.append(block)
                                    index += 1
                            else:
                                block.index = index
                                target.append(block)
                                index += 1
                    elif sub_tag == "tbl":
                        table = self._parse_table(
                            sub_elem, index, bindata, header_index
                        )
                        if table:
                            target.append(table)
                            index += 1

    def _process_p(
        self,
        p: ET.Element,
        body: list[Paragraph | Table | ImageRef],
        index: int,
        bindata: dict[str, tuple[bytes, str]] | None = None,
        header_index: HeaderIndex | None = None,
        headers: list[Paragraph | Table | ImageRef] | None = None,
        footers: list[Paragraph | Table | ImageRef] | None = None,
    ) -> int:
        for block in self._parse_paragraph_blocks(
            p, bindata, header_index, headers=headers, footers=footers
        ):
            block.index = index
            body.append(block)
            index += 1

        return index

    def _parse_paragraph_blocks(
        self,
        p: ET.Element,
        bindata: dict[str, tuple[bytes, str]] | None = None,
        header_index: HeaderIndex | None = None,
        headers: list[Paragraph | Table | ImageRef] | None = None,
        footers: list[Paragraph | Table | ImageRef] | None = None,
    ) -> list[Paragraph | Table | ImageRef]:
        blocks: list[Paragraph | Table | ImageRef] = []
        runs: list[Run] = []
        text_parts: list[str] = []
        style = self._detect_style(p, header_index)
        level = self._paragraph_level(p, header_index)
        align = self._paragraph_align(p, header_index)
        style_name = self._paragraph_style_name(p, header_index)
        char_shapes = header_index.char_shapes if header_index else None

        def flush_paragraph() -> None:
            text = "".join(text_parts)
            if not text.strip():
                runs.clear()
                text_parts.clear()
                return
            blocks.append(
                Paragraph(
                    text=text,
                    style=style,
                    level=level,
                    runs=list(runs),
                    index=0,
                    align=align,
                    style_name=style_name,
                )
            )
            runs.clear()
            text_parts.clear()

        # field_id -> URL for currently open HYPERLINK spans
        active_hrefs: dict[str, str] = {}

        def _current_href() -> str | None:
            # Return the most recently opened still-active hyperlink.
            return next(reversed(active_hrefs.values()), None) if active_hrefs else None

        def append_text(text: str, fmt: CharShape | None) -> None:
            if not text:
                return
            shape = fmt or CharShape()
            runs.append(
                Run(
                    text=text,
                    bold=shape.bold,
                    italic=shape.italic,
                    underline=shape.underline,
                    font_size=shape.font_size,
                    color=shape.color,
                    font_face=shape.font_face,
                    href=_current_href(),
                )
            )
            text_parts.append(text)

        def _handle_ctrl(ctrl_elem: ET.Element) -> None:
            for child in ctrl_elem:
                ctag = _strip_ns(child.tag)
                if ctag == "fieldBegin" and child.get("type") == "HYPERLINK":
                    url = _extract_hyperlink_url(child)
                    if url:
                        active_hrefs[child.get("id", "")] = url
                elif ctag == "fieldEnd":
                    begin_ref = child.get("beginIDRef", "")
                    active_hrefs.pop(begin_ref, None)
                elif ctag == "header" and headers is not None:
                    self._parse_header_footer(child, headers, bindata, header_index)
                elif ctag == "footer" and footers is not None:
                    self._parse_header_footer(child, footers, bindata, header_index)

        def walk(node: ET.Element, fmt: CharShape | None = None) -> None:
            for child in node:
                tag = _strip_ns(child.tag)
                if tag in _SKIP_TAGS:
                    continue
                if tag == "run":
                    ref = child.get("charPrIDRef")
                    next_fmt = (
                        char_shapes.get(ref) if char_shapes and ref else None
                    ) or fmt
                    walk(child, next_fmt)
                elif tag == "t" and child.text:
                    append_text(child.text, fmt)
                elif tag == "lineBreak":
                    append_text("\n", fmt)
                elif tag in _SPACE_TAGS:
                    append_text(" ", fmt)
                elif tag in _TEXT_BOX_TAGS:
                    text = self._extract_control_text(child, char_shapes, fmt)
                    if text:
                        append_text(text, fmt)
                elif tag in _NOTE_TAGS:
                    text = self._extract_control_text(child, char_shapes, fmt)
                    if text:
                        append_text(f"[{tag}: {text}]", fmt)
                elif tag in _EQUATION_TAGS:
                    append_text(self._equation_placeholder(child), fmt)
                elif tag == "ctrl":
                    _handle_ctrl(child)
                elif tag == "tbl":
                    flush_paragraph()
                    table = self._parse_table(child, 0, bindata, header_index)
                    if table:
                        blocks.append(table)
                elif tag in _INLINE_OBJECT_TAGS:
                    flush_paragraph()
                    image = self._parse_image(child, 0, bindata)
                    if image:
                        blocks.append(image)
                elif tag not in _SKIP_TAGS:
                    walk(child, fmt)

        walk(p)
        flush_paragraph()
        return blocks

    def _extract_control_text(
        self,
        elem: ET.Element,
        char_shapes: dict[str, CharShape] | None = None,
        run_fmt: CharShape | None = None,
    ) -> str:
        text_parts: list[str] = []
        runs: list[Run] = []
        self._collect_text(elem, text_parts, runs, char_shapes, run_fmt)
        return "".join(text_parts).strip()

    def _equation_placeholder(self, elem: ET.Element) -> str:
        eq_parts: list[str] = []
        for desc in elem.iter():
            if _strip_ns(desc.tag) == "t" and desc.text:
                eq_parts.append(desc.text)
        text = "".join(eq_parts).strip()
        return f"[수식: {text}]" if text else "[수식]"

    def _collect_text(
        self,
        elem: ET.Element,
        text_parts: list[str],
        runs: list[Run],
        char_shapes: dict[str, CharShape] | None = None,
        _run_fmt: CharShape | None = None,
    ) -> None:
        for child in elem:
            tag = _strip_ns(child.tag)
            if tag in _INLINE_OBJECT_TAGS:
                continue
            if tag == "run":
                ref = child.get("charPrIDRef")
                fmt = (
                    char_shapes.get(ref) if char_shapes and ref else None
                ) or _run_fmt
                self._collect_text(child, text_parts, runs, char_shapes, fmt)
            elif tag == "t" and child.text:
                fmt = _run_fmt or CharShape()
                runs.append(
                    Run(
                        text=child.text,
                        bold=fmt.bold,
                        italic=fmt.italic,
                        underline=fmt.underline,
                        font_size=fmt.font_size,
                        color=fmt.color,
                        font_face=fmt.font_face,
                    )
                )
                text_parts.append(child.text)
            elif tag == "lineBreak":
                text_parts.append("\n")
            elif tag in _SPACE_TAGS:
                text_parts.append(" ")
            elif tag in _TEXT_BOX_TAGS:
                # Text boxes keep paragraph structure internally; inline the text here.
                gso_parts: list[str] = []
                self._collect_text(child, gso_parts, [], char_shapes)
                if gso_parts:
                    text = "".join(gso_parts).strip()
                    if text:
                        runs.append(Run(text=text))
                        text_parts.append(text)
            elif tag in _NOTE_TAGS:
                # Inline footnotes and endnotes at the reference point.
                note_parts: list[str] = []
                self._collect_text(child, note_parts, [], char_shapes)
                text = "".join(note_parts).strip()
                if text:
                    note = f"[{tag}: {text}]"
                    runs.append(Run(text=note))
                    text_parts.append(note)
            elif tag in _EQUATION_TAGS:
                # Preserve any readable equation text as a placeholder run.
                eq = self._equation_placeholder(child)
                runs.append(Run(text=eq))
                text_parts.append(eq)
            else:
                self._collect_text(child, text_parts, runs, char_shapes, _run_fmt)

    def _paragraph_level(
        self, p: ET.Element, header_index: HeaderIndex | None = None
    ) -> int:
        outline = p.get("outlineLevel") or p.get("OutlineLevel")
        if not outline and header_index:
            pref = p.get("paraPrIDRef") or p.get("paraPrIdRef")
            if pref:
                outline = header_index.para_shapes.get(pref, ParaShape()).outline_level
        return _parse_int(
            outline,
            default=0,
            field="paragraph outlineLevel",
            strict=self.strict,
            logger=logger,
        )

    def _paragraph_align(
        self, p: ET.Element, header_index: HeaderIndex | None = None
    ) -> str | None:
        if not header_index:
            return None
        pref = p.get("paraPrIDRef") or p.get("paraPrIdRef")
        if not pref:
            return None
        align = header_index.para_shapes.get(pref, ParaShape()).align
        return align or None

    def _paragraph_style_name(
        self, p: ET.Element, header_index: HeaderIndex | None = None
    ) -> str | None:
        if not header_index:
            return None
        style_id = p.get("styleIDRef", "") or p.get("styleId", "")
        if not style_id:
            return None
        return header_index.styles.get(style_id)

    def _detect_style(
        self,
        p: ET.Element,
        header_index: HeaderIndex | None = None,
    ) -> ParagraphStyle:
        """Return the ParagraphStyle for a paragraph element."""
        if self.heading_detection != "none":
            outline = p.get("outlineLevel") or p.get("OutlineLevel")
            if not outline and header_index:
                pref = p.get("paraPrIDRef") or p.get("paraPrIdRef")
                if pref:
                    outline = header_index.para_shapes.get(
                        pref, ParaShape()
                    ).outline_level
            if outline and outline in _HEADING_STYLES:
                return _HEADING_STYLES[outline]
            style_id = p.get("styleIDRef", "") or p.get("styleId", "")
            style_name = header_index.styles.get(style_id, "") if header_index else ""
            combined = (style_id + style_name).lower()
            heading_match = re.search(r"(heading|head)\s*([1-6])", combined)
            if heading_match:
                return _HEADING_STYLES.get(
                    heading_match.group(2), ParagraphStyle.HEADING1
                )
            if "head" in combined or "title" in combined:
                return ParagraphStyle.HEADING1
        if header_index:
            pref = p.get("paraPrIDRef") or p.get("paraPrIdRef")
            list_kind = header_index.para_shapes.get(pref or "", ParaShape()).list_kind
            if list_kind == "ordered":
                return ParagraphStyle.LIST_ORDERED
            if list_kind == "unordered":
                return ParagraphStyle.LIST_UNORDERED
        combined_for_list = (p.get("styleIDRef", "") or p.get("styleId", "")).lower()
        if "list" in combined_for_list or "bullet" in combined_for_list:
            return ParagraphStyle.LIST_UNORDERED
        if self.heading_detection == "auto" and header_index:
            inferred = self._infer_heading_from_runs(p, header_index)
            if inferred:
                return inferred
        return ParagraphStyle.BODY

    def _infer_heading_from_runs(
        self,
        p: ET.Element,
        header_index: HeaderIndex,
    ) -> ParagraphStyle | None:
        """Heuristic: infer heading level from dominant font size and face.

        Korean documents rarely use Hancom's structural heading styles.
        Instead, heading-like paragraphs use large or bold-display font faces
        (HY헤드라인M, 한양중고딕, etc.) with sizes above the body baseline.
        Only fires on short paragraphs (< 120 chars) to avoid false positives
        on body sentences that happen to share a font face.
        """
        # Collect all charPrIDRef references used by this paragraph's runs.
        sizes: list[float] = []
        is_heading_face = False
        is_body_face = False
        is_bold = False
        total_text_len = 0

        for run_elem in p.iter():
            if _strip_ns(run_elem.tag) != "run":
                continue
            ref = run_elem.get("charPrIDRef")
            shape = header_index.char_shapes.get(ref) if ref else None
            if shape:
                if shape.font_size:
                    sizes.append(shape.font_size)
                if shape.font_face and shape.font_face in _HEADING_FONT_FACES:
                    is_heading_face = True
                if shape.font_face and shape.font_face in _BODY_FONT_FACES:
                    is_body_face = True
                if shape.bold:
                    is_bold = True
            for t_elem in run_elem:
                if _strip_ns(t_elem.tag) == "t" and t_elem.text:
                    total_text_len += len(t_elem.text)

        if not sizes or total_text_len > 120:
            return None

        if is_body_face:
            return None

        max_size = max(sizes)

        if is_heading_face:
            if max_size >= 14:
                return ParagraphStyle.HEADING1
            if max_size >= 12:
                return ParagraphStyle.HEADING2
            # Heading face below 12pt is usually annotation-sized, not a heading.
            return None
        # Without a heading face, size alone is ambiguous; require bold too.
        # 10-11pt is Hancom's default body size, but some templates use
        # 16pt non-bold body text.
        if not is_bold:
            return None
        if max_size >= 18:
            return ParagraphStyle.HEADING1
        if max_size >= 16:
            return ParagraphStyle.HEADING2
        return None

    def _parse_table(
        self,
        tbl: ET.Element,
        index: int,
        bindata: dict[str, tuple[bytes, str]] | None = None,
        header_index: HeaderIndex | None = None,
    ) -> Table | None:
        rows: list[Row] = []
        caption = self._table_caption(tbl, header_index)

        for tr in tbl:
            if _strip_ns(tr.tag) != "tr":
                continue
            cells: list[Cell] = []
            for tc in tr:
                if _strip_ns(tc.tag) != "tc":
                    continue
                # Cell spans live on a child <cellSpan>, not on <tc> itself.
                col_span = 1
                row_span = 1
                for child in tc:
                    if _strip_ns(child.tag) == "cellSpan":
                        col_span = _parse_int(
                            child.get("colSpan"),
                            default=1,
                            field="table cell colSpan",
                            strict=self.strict,
                            logger=logger,
                        )
                        row_span = _parse_int(
                            child.get("rowSpan"),
                            default=1,
                            field="table cell rowSpan",
                            strict=self.strict,
                            logger=logger,
                        )
                        break
                blocks = self._parse_cell_blocks(tc, bindata, header_index)
                cells.append(
                    Cell(
                        col_span=col_span,
                        row_span=row_span,
                        blocks=blocks,
                    )
                )
            if cells:
                rows.append(Row(cells=cells))

        if not rows:
            return None

        return Table(rows=rows, caption=caption, index=index)

    def _table_caption(
        self, tbl: ET.Element, header_index: HeaderIndex | None = None
    ) -> str | None:
        attr_caption = (tbl.get("caption") or tbl.get("title") or "").strip()
        if attr_caption:
            return attr_caption
        char_shapes = header_index.char_shapes if header_index else None
        for child in tbl:
            if _strip_ns(child.tag) != "caption":
                continue
            text = self._extract_control_text(child, char_shapes).strip()
            if text:
                return text
        return None

    def _parse_cell_blocks(
        self,
        elem: ET.Element,
        bindata: dict[str, tuple[bytes, str]] | None = None,
        header_index: HeaderIndex | None = None,
    ) -> list[Paragraph | Table | ImageRef]:
        blocks: list[Paragraph | Table | ImageRef] = []

        def append_block(block: Paragraph | Table | ImageRef) -> None:
            block.index = len(blocks)
            blocks.append(block)

        def walk(node: ET.Element) -> None:
            for child in node:
                tag = _strip_ns(child.tag)
                if tag in _SKIP_TAGS:
                    continue
                if tag == "p":
                    for block in self._parse_paragraph_blocks(
                        child, bindata, header_index
                    ):
                        append_block(block)
                elif tag == "tbl":
                    table = self._parse_table(child, len(blocks), bindata, header_index)
                    if table:
                        append_block(table)
                elif tag in _INLINE_OBJECT_TAGS:
                    image = self._parse_image(child, len(blocks), bindata)
                    if image:
                        append_block(image)
                else:
                    walk(child)

        walk(elem)
        return blocks

    def _has_text(self, blocks: list[Paragraph | Table | ImageRef]) -> bool:
        for block in blocks:
            if isinstance(block, Paragraph) and block.text.strip():
                return True
            if isinstance(block, Table):
                for row in block.rows:
                    for cell in row.cells:
                        if self._has_text(cell.blocks):
                            return True
        return False

    def _parse_image(
        self,
        elem: ET.Element,
        index: int,
        bindata: dict[str, tuple[bytes, str]] | None = None,
    ) -> ImageRef | None:
        caption = elem.get("caption") or elem.get("title")
        width = height = None
        data: bytes | None = None
        fmt: str | None = None

        try:
            for child in elem.iter():
                tag = _strip_ns(child.tag)
                if tag in ("sz", "curSz"):
                    w = child.get("width") or child.get("w")
                    h = child.get("height") or child.get("h")
                    if w:
                        width = int(float(w))
                    if h:
                        height = int(float(h))
                elif tag == "img" and bindata:
                    ref = child.get("binaryItemIDRef")
                    if ref:
                        ref_id = ref.strip()
                        if ref_id in bindata:
                            data, fmt = bindata[ref_id]
                        else:
                            try:
                                numeric_ref = str(int(ref_id))
                            except ValueError:
                                numeric_ref = ""
                            if numeric_ref and numeric_ref in bindata:
                                data, fmt = bindata[numeric_ref]
        except (ValueError, TypeError):
            pass

        return ImageRef(
            index=index,
            caption=caption,
            width=width,
            height=height,
            data=data,
            format=fmt,
        )
