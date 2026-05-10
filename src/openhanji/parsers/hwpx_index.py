"""HWPX archive, package, metadata, and header indexing helpers."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime

from openhanji.exceptions import CorruptedFileError
from openhanji.models.document import Metadata
from openhanji.parsers.hwpx_support import (
    _BULLET_NUM_FORMATS,
    CharShape,
    HeaderIndex,
    ParaShape,
    _parse_int,
    _resolve_part,
    _strip_ns,
)

logger = logging.getLogger(__name__)


def parse_metadata(
    zf: zipfile.ZipFile, names: list[str], *, strict: bool = False
) -> Metadata:
    """Build Metadata from header.xml and content.hpf."""
    meta = Metadata()

    header = next((n for n in names if n.endswith("header.xml")), None)
    if header:
        try:
            with zf.open(header) as f:
                header_xml = ET.parse(f).getroot()
            for elem in header_xml.iter():
                tag = _strip_ns(elem.tag)
                text = (elem.text or "").strip()
                if not text:
                    continue
                if tag == "title":
                    meta.title = text
                elif tag in ("creator", "author"):
                    meta.author = text
                elif tag == "subject":
                    meta.subject = text
        except ET.ParseError as exc:
            if strict:
                raise CorruptedFileError("Parse error in header.xml") from exc
            logger.warning("Could not parse header.xml: %s", exc)

    hpf = next((n for n in names if n.endswith("content.hpf")), None)
    if hpf:
        try:
            with zf.open(hpf) as f:
                hpf_xml = ET.parse(f).getroot()
            for elem in hpf_xml.iter():
                tag = _strip_ns(elem.tag)
                text = (elem.text or "").strip()
                name_attr = elem.get("name", "")
                if tag == "title" and text and meta.title is None:
                    meta.title = text
                elif tag == "meta":
                    if name_attr == "creator" and text and meta.author is None:
                        meta.author = text
                    elif name_attr == "subject" and text and meta.subject is None:
                        meta.subject = text
                    elif name_attr == "CreatedDate" and text:
                        try:
                            meta.created_at = datetime.fromisoformat(
                                text.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass
                    elif name_attr == "ModifiedDate" and text:
                        try:
                            meta.modified_at = datetime.fromisoformat(
                                text.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass
                    elif name_attr == "keyword" and text:
                        meta.keywords = [
                            k.strip()
                            for k in re.split(r"[,\r\n]+", text)
                            if k.strip()
                        ]
                    elif name_attr.lower() == "pagecount" and text:
                        try:
                            meta.page_count = int(text)
                        except ValueError:
                            pass
        except ET.ParseError as exc:
            if strict:
                raise CorruptedFileError("Parse error in content.hpf") from exc
            logger.warning("Could not parse content.hpf: %s", exc)

    return meta


def parse_package(
    zf: zipfile.ZipFile,
    names: list[str],
    *,
    strict: bool = False,
) -> dict[str, object]:
    content_path = next((n for n in names if n.endswith("content.hpf")), None)
    package: dict[str, object] = {
        "content_path": content_path,
        "manifest": {},
        "spine": [],
    }
    if not content_path:
        return package

    try:
        with zf.open(content_path) as f:
            package_xml = ET.parse(f).getroot()
    except ET.ParseError as exc:
        if strict:
            raise CorruptedFileError("Parse error in content.hpf") from exc
        logger.warning("Could not parse content.hpf: %s", exc)
        return package

    manifest: dict[str, str] = {}
    for elem in package_xml.iter():
        if _strip_ns(elem.tag) != "item":
            continue
        item_id = elem.get("id")
        href = elem.get("href")
        if item_id and href:
            manifest[item_id] = _resolve_manifest_href(content_path, href, names)
    package["manifest"] = manifest

    spine: list[str] = []
    for elem in package_xml.iter():
        if _strip_ns(elem.tag) != "itemref":
            continue
        idref = elem.get("idref")
        if not idref:
            continue
        target = manifest.get(idref)
        if not target:
            continue
        resolved = match_name(target, names)
        if not resolved:
            continue
        spine.append(resolved)
    package["spine"] = spine

    return package


def index_bindata(
    zf: zipfile.ZipFile,
    names: list[str],
    *,
    with_images: bool,
) -> dict[str, tuple[bytes, str]]:
    """Return {binaryItemIDRef: (bytes, ext)} for every BinData/ entry."""
    if not with_images:
        return {}
    index: dict[str, tuple[bytes, str]] = {}
    for name in names:
        if not name.lower().startswith("bindata/"):
            continue
        stem = name.rsplit("/", 1)[-1]
        ext = stem.rsplit(".", 1)[-1].lower() if "." in stem else ""
        stem_no_ext = stem.rsplit(".", 1)[0] if "." in stem else stem
        m = re.search(r"(\d+)", stem_no_ext)
        try:
            data = zf.read(name)
        except Exception as exc:
            logger.warning("Could not read BinData entry %s: %s", name, exc)
            continue
        index[stem_no_ext] = (data, ext)
        if m:
            index[str(int(m.group(1)))] = (data, ext)
    return index


def index_header(
    zf: zipfile.ZipFile, names: list[str], *, strict: bool = False
) -> HeaderIndex:
    index = HeaderIndex()
    header = next((n for n in names if n.endswith("header.xml")), None)
    if not header:
        return index
    try:
        with zf.open(header) as f:
            header_xml = ET.parse(f).getroot()
        for elem in header_xml.iter():
            tag = _strip_ns(elem.tag)
            if tag == "fontface":
                lang = (elem.get("lang") or "").upper()
                if not lang:
                    continue
                fonts = index.font_faces.setdefault(lang, {})
                for font in elem:
                    if _strip_ns(font.tag) != "font":
                        continue
                    font_id = font.get("id")
                    face = font.get("face")
                    if font_id and face:
                        fonts[font_id] = face
            elif tag == "charPr":
                cid = elem.get("id")
                if cid is None:
                    continue
                bold = elem.get("bold", "0") == "1"
                italic = elem.get("italic", "0") == "1"
                ul_elem = elem.find(".//{*}underline")
                underline = (
                    ul_elem is not None and ul_elem.get("type", "NONE") != "NONE"
                )
                raw_h = elem.get("height")
                font_height = _parse_int(
                    raw_h,
                    default=0,
                    field="header.xml charPr height",
                    strict=strict,
                    logger=logger,
                )
                font_size: float | None = (
                    round(font_height / 100, 1) if font_height else None
                )
                raw_color = elem.get("textColor", "")
                color: str | None = (
                    raw_color if raw_color and raw_color.upper() != "#000000" else None
                )
                font_ref = elem.find(".//{*}fontRef")
                font_face: str | None = None
                font_face_latin: str | None = None
                if font_ref is not None:
                    h_ref = font_ref.get("hangul")
                    l_ref = font_ref.get("latin")
                    if h_ref and "HANGUL" in index.font_faces:
                        font_face = index.font_faces["HANGUL"].get(h_ref)
                    if l_ref and "LATIN" in index.font_faces:
                        font_face_latin = index.font_faces["LATIN"].get(l_ref)
                    if font_face is None:
                        font_face = font_face_latin
                index.char_shapes[cid] = CharShape(
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    font_size=font_size,
                    color=color,
                    font_face=font_face,
                    font_face_latin=font_face_latin,
                )
            elif tag == "numbering":
                nid = elem.get("id")
                if nid is None:
                    continue
                first_head = elem.find(".//{*}paraHead")
                if first_head is not None:
                    nfmt = first_head.get("numFormat", "DIGIT")
                    index.numbering[nid] = (
                        "unordered" if nfmt in _BULLET_NUM_FORMATS else "ordered"
                    )
            elif tag == "paraPr":
                pid = elem.get("id")
                if pid is None:
                    continue
                list_kind = ""
                for desc in elem.iter():
                    dtag = _strip_ns(desc.tag)
                    if dtag == "heading":
                        htype = desc.get("type", "")
                        hidref = desc.get("idRef", "0")
                        if htype == "NUMBER" and hidref != "0":
                            list_kind = index.numbering.get(hidref, "ordered")
                        break
                    if dtag in ("autoNumFormat", "numPr"):
                        list_kind = "ordered"
                        break
                    if dtag in ("bullet", "bulletPr"):
                        list_kind = "unordered"
                        break
                align = ""
                align_elem = elem.find(".//{*}align")
                if align_elem is not None:
                    align = align_elem.get("horizontal", "")
                outline_level = elem.get("outlineLevel", "")
                heading_child = elem.find(".//{*}heading")
                if heading_child is not None:
                    if heading_child.get("type") == "OUTLINE":
                        child_level = heading_child.get("level", "0")
                        if child_level and child_level != "0":
                            outline_level = child_level
                index.para_shapes[pid] = ParaShape(
                    outline_level=outline_level,
                    list_kind=list_kind,
                    align=align,
                )
            elif tag == "style":
                sid = elem.get("id")
                if sid is None:
                    continue
                name = (
                    elem.get("name")
                    or elem.get("engName")
                    or elem.get("localName")
                    or ""
                ).strip()
                if name:
                    index.styles[sid] = name
    except ET.ParseError as exc:
        if strict:
            raise CorruptedFileError("Parse error in header.xml") from exc
        logger.warning("Could not index header.xml: %s", exc)
    return index


def section_files(names: list[str], package: dict[str, object]) -> list[str]:
    spine = package.get("spine")
    if isinstance(spine, list) and spine:
        spine_sections = [
            name for name in spine if isinstance(name, str) and _is_section_file(name)
        ]
        if spine_sections:
            return spine_sections
    return sorted(
        [n for n in names if _is_section_file(n)],
        key=section_order,
    )


def _resolve_manifest_href(content_path: str, href: str, names: list[str]) -> str:
    zip_root_path = href.lstrip("/")
    package_relative_path = _resolve_part(content_path, href)
    if "/" in zip_root_path:
        candidates = [zip_root_path, package_relative_path]
    else:
        candidates = [package_relative_path, zip_root_path]
    for candidate in candidates:
        resolved = match_name(candidate, names)
        if resolved:
            return resolved
    return candidates[-1]


def _is_section_file(name: str) -> bool:
    return re.search(r"section\d*\.xml$", name, re.IGNORECASE) is not None


def match_name(name: str, names: list[str]) -> str | None:
    if name in names:
        return name
    lower_names = {entry.lower(): entry for entry in names}
    return lower_names.get(name.lower())


def section_order(name: str) -> int:
    m = re.search(r"section(\d+)", name, re.IGNORECASE)
    return int(m.group(1)) if m else 999
