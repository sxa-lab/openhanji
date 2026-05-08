"""Shared pytest fixtures for integration tests."""

from __future__ import annotations

import pathlib
import zipfile

import pytest


def sec(body: str) -> str:
    """Wrap body XML in a minimal hs:sec element with all required namespaces."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
        ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
        ' xmlns:ht="http://www.hancom.co.kr/hwpml/2011/table">'
        + body
        + "</hs:sec>"
    )


def make_hwpx(
    tmp_path: pathlib.Path,
    name: str,
    section_xml: str,
    header_xml: str = "<hh:head/>",
) -> pathlib.Path:
    """Build a minimal HWPX zip with the given section XML and return its path."""
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Contents/header.xml", header_xml)
        zf.writestr("Contents/section0.xml", section_xml)
    return path


@pytest.fixture()
def make_doc(tmp_path: pathlib.Path):
    """Fixture: factory that creates a one-section HWPX from body XML.

    Usage::

        def it_parses_something(make_doc):
            doc = make_doc("<hp:p><hp:run><hp:t>hello</hp:t></hp:run></hp:p>")
    """
    def _factory(body_xml: str, header_xml: str = "<hh:head/>") -> pathlib.Path:
        return make_hwpx(tmp_path, "test.hwpx", sec(body_xml), header_xml)

    return _factory
