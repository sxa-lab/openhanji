"""CLI entry point, extract and info subcommands."""

from __future__ import annotations

import pathlib
import sys
from typing import cast

import click

import openhanji
from openhanji.parsers.base import HeadingDetection


@click.group()
@click.version_option(openhanji.__version__, "--version", "-v")
def main() -> None:
    """OpenHanji, a Hancom Office document parser."""


_EXT_MAP = {"markdown": ".md", "json": ".json", "text": ".txt"}


@main.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.option(
    "--format", "-f",
    type=click.Choice(["markdown", "json", "text"], case_sensitive=False),
    default="markdown",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--out", "-o",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help="Output file (single-file mode) or output directory (directory mode).",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Raise errors on unknown content instead of skipping.",
)
@click.option(
    "--with-images",
    is_flag=True,
    default=False,
    help="Read and embed image binaries. Default skips binary reads; "
         "images render as placeholders.",
)
@click.option(
    "--heading-detection",
    type=click.Choice(["auto", "structural", "none"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Heading detection strategy: auto (structural + font heuristic), "
         "structural (outline/style only), none (all paragraphs are BODY).",
)
def extract(
    path: pathlib.Path,
    format: str,
    out: pathlib.Path | None,
    strict: bool,
    with_images: bool,
    heading_detection: str,
) -> None:
    """Extract document content as markdown, json, or text.

    PATH may be a single .hwpx file or a directory. In directory mode --out
    is required and must point to an (existing or new) directory.
    """
    fmt = format.lower()

    if path.is_dir():
        if out is None:
            click.echo("Error: --out is required when PATH is a directory.", err=True)
            sys.exit(1)
        out.mkdir(parents=True, exist_ok=True)
        files = sorted(path.rglob("*.hwpx"))
        if not files:
            click.echo(f"No .hwpx files found in {path}", err=True)
            sys.exit(1)
        hd = cast(HeadingDetection, heading_detection)
        errors = 0
        for hwpx in files:
            try:
                doc = openhanji.open(
                    hwpx, strict=strict, with_images=with_images, heading_detection=hd
                )
            except (openhanji.OpenHanjiError, FileNotFoundError) as exc:
                click.echo(f"Error [{hwpx.name}]: {exc}", err=True)
                errors += 1
                continue
            output = _render(doc, fmt)
            dest = out / (hwpx.stem + _EXT_MAP[fmt])
            dest.write_text(output, encoding="utf-8")
            click.echo(f"Written to {dest}")
        if errors:
            sys.exit(1)
    else:
        hd = cast(HeadingDetection, heading_detection)
        try:
            doc = openhanji.open(
                path, strict=strict, with_images=with_images, heading_detection=hd
            )
        except (openhanji.OpenHanjiError, FileNotFoundError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        output = _render(doc, fmt)
        if out:
            out.write_text(output, encoding="utf-8")
            click.echo(f"Written to {out}")
        else:
            click.echo(output)


def _render(doc: openhanji.Document, fmt: str) -> str:
    if fmt == "json":
        return doc.to_json()
    if fmt == "text":
        return doc.to_text()
    return doc.to_markdown()


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=pathlib.Path))
def info(path: pathlib.Path) -> None:
    """Print title, author, dates, and body counts."""
    try:
        doc = openhanji.open(path)
    except openhanji.OpenHanjiError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    m = doc.metadata
    rows: list[tuple[str, str]] = []
    if m.title:
        rows.append(("Title", m.title))
    if m.author:
        rows.append(("Author", m.author))
    if m.subject:
        rows.append(("Subject", m.subject))
    if m.keywords:
        rows.append(("Keywords", ", ".join(m.keywords)))
    if m.created_at:
        rows.append(("Created", str(m.created_at)))
    if m.modified_at:
        rows.append(("Modified", str(m.modified_at)))
    if m.page_count is not None:
        rows.append(("Pages", str(m.page_count)))
    rows.extend([
        ("Paragraphs", str(len(doc.paragraphs))),
        ("Tables", str(len(doc.tables))),
        ("Images", str(len(doc.images))),
    ])
    width = max(len(k) for k, _ in rows)
    for key, val in rows:
        click.echo(f"  {key:<{width}}  {val}")
