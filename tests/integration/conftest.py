"""Shared pytest fixtures for integration tests."""

from __future__ import annotations

import pathlib

import pytest

from tests.integration.builders import make_hwpx, sec  # noqa: F401


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
