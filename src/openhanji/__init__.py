from __future__ import annotations

import pathlib
from typing import Literal

from openhanji.document import (
    Cell,
    Document,
    ImageRef,
    Metadata,
    Paragraph,
    ParagraphStyle,
    Row,
    Run,
    Section,
    Table,
)
from openhanji.exceptions import (
    CorruptedFileError,
    NotSupportedError,
    OpenHanjiError,
    UnknownRecordError,
)

__version__ = "0.1.0"
__all__ = [
    "open",
    "Document",
    "Section",
    "Paragraph",
    "Run",
    "Table",
    "Row",
    "Cell",
    "ImageRef",
    "Metadata",
    "ParagraphStyle",
    "OpenHanjiError",
    "NotSupportedError",
    "CorruptedFileError",
    "UnknownRecordError",
]

_SUPPORTED_V01 = {".hwpx"}


_HEADING_DETECTION_VALUES = frozenset({"auto", "structural", "none"})


def open(
    path: str | pathlib.Path,
    *,
    strict: bool = False,
    with_images: bool = False,
    heading_detection: Literal["auto", "structural", "none"] = "auto",
) -> Document:
    if heading_detection not in _HEADING_DETECTION_VALUES:
        raise ValueError(
            f"heading_detection must be 'auto', 'structural', or 'none'; "
            f"got {heading_detection!r}"
        )
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_V01:
        raise NotSupportedError(f"{suffix!r} is not supported.")
    from openhanji.parsers.hwpx import HwpxParser
    parser = HwpxParser(
        strict=strict,
        with_images=with_images,
        heading_detection=heading_detection,
    )
    return parser.parse(path)
