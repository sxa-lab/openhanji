from __future__ import annotations

import pathlib
from typing import Literal

from openhanji.exceptions import (
    CorruptedFileError,
    NotSupportedError,
    OpenHanjiError,
    UnknownRecordError,
)
from openhanji.models.document import (
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
from openhanji.parsers.base import HancomDocument

__version__ = "0.1.0"
__all__ = [
    "open",
    "Document",
    "HancomDocument",
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

_SUPPORTED_EXTENSIONS = {".hwpx", ".hwp", ".cell", ".show"}

_HEADING_DETECTION_VALUES = frozenset({"auto", "structural", "none"})


def open(
    path: str | pathlib.Path,
    *,
    strict: bool = False,
    with_images: bool = False,
    heading_detection: Literal["auto", "structural", "none"] = "auto",
) -> HancomDocument:
    if heading_detection not in _HEADING_DETECTION_VALUES:
        raise ValueError(
            f"heading_detection must be 'auto', 'structural', or 'none'; "
            f"got {heading_detection!r}"
        )
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")
    suffix = path.suffix.lower()

    if suffix == ".hwpx":
        from openhanji.parsers.hwpx import HwpxParser

        return HwpxParser(
            strict=strict,
            with_images=with_images,
            heading_detection=heading_detection,
        ).parse(path)
    if suffix == ".hwp":
        raise NotSupportedError("'.hwp' is not yet implemented. Coming soon!")
    if suffix == ".cell":
        raise NotSupportedError("'.cell' is not yet implemented. Coming soon!")
    if suffix == ".show":
        raise NotSupportedError("'.show' is not yet implemented. Coming soon!")
    raise NotSupportedError(
        f"'{suffix}' is not a supported Hancom Office format. "
        f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
    )
