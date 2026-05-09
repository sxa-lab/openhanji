"""BaseParser ABC, all format parsers implement parse(path) -> HancomDocument."""

from __future__ import annotations

import abc
import pathlib
from collections.abc import Sequence
from datetime import datetime
from typing import Literal, Protocol, runtime_checkable

HeadingDetection = Literal["auto", "structural", "none"]


@runtime_checkable
class HancomMetadata(Protocol):
    """Common metadata exposed by all supported Hancom document models."""

    @property
    def title(self) -> str | None: ...

    @property
    def author(self) -> str | None: ...

    @property
    def created_at(self) -> datetime | None: ...

    @property
    def modified_at(self) -> datetime | None: ...

    @property
    def page_count(self) -> int | None: ...

    @property
    def subject(self) -> str | None: ...

    @property
    def keywords(self) -> Sequence[str]: ...


@runtime_checkable
class HancomDocument(Protocol):
    """Structural protocol satisfied by all openhanji document model types."""

    @property
    def metadata(self) -> HancomMetadata: ...

    @property
    def paragraphs(self) -> Sequence[object]: ...

    @property
    def tables(self) -> Sequence[object]: ...

    @property
    def images(self) -> Sequence[object]: ...

    def to_markdown(self) -> str: ...
    def to_text(self) -> str: ...


class BaseParser(abc.ABC):
    def __init__(
        self,
        strict: bool = False,
        with_images: bool = False,
        heading_detection: HeadingDetection = "auto",
    ) -> None:
        self.strict = strict
        self.with_images = with_images
        self.heading_detection: HeadingDetection = heading_detection

    @abc.abstractmethod
    def parse(self, path: pathlib.Path) -> HancomDocument: ...
