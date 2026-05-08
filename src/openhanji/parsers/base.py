"""BaseParser ABC, all format parsers implement parse(path) -> Document."""

from __future__ import annotations

import abc
import pathlib
from typing import Literal

from openhanji.document import Document

HeadingDetection = Literal["auto", "structural", "none"]


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
    def parse(self, path: pathlib.Path) -> Document: ...
