"""Converts a Document to JSON."""

from __future__ import annotations

import json
from typing import Literal

from openhanji.models.document import Document

JsonMode = Literal["flat", "structured"]

_JSON_MODES = frozenset({"flat", "structured"})


def to_json(doc: Document, indent: int = 2, *, mode: JsonMode = "flat") -> str:
    if mode not in _JSON_MODES:
        raise ValueError(f"mode must be 'flat' or 'structured'; got {mode!r}")
    if mode == "structured":
        data: dict[str, object] = {
            "metadata": doc.metadata.to_dict(),
            "sections": [section.to_dict() for section in doc.sections],
        }
    else:
        data = {
            "metadata": doc.metadata.to_dict(),
            "body": [block.to_dict() for block in doc.blocks],
        }
        if doc.headers:
            data["headers"] = [block.to_dict() for block in doc.headers]
        if doc.footers:
            data["footers"] = [block.to_dict() for block in doc.footers]
    return json.dumps(data, ensure_ascii=False, indent=indent)
