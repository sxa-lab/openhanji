"""CLI entry point, extract and info subcommands."""

from __future__ import annotations

import pathlib
import sys
import time
from typing import cast

import click
import tqdm as tqdm_mod

import openhanji
from openhanji.converters.json import to_json
from openhanji.models.document import Document
from openhanji.parsers.base import HancomDocument, HeadingDetection


@click.group()
@click.version_option(openhanji.__version__, "--version", "-v")
def main() -> None:
    """OpenHanji, a Hancom Office document parser."""


_SUPPORTED_EXTENSIONS = {".hwpx", ".hwp", ".cell", ".show"}
_EXT_MAP = {"markdown": ".md", "json": ".json", "text": ".txt"}


def _safe_path(candidate: pathlib.Path) -> pathlib.Path:
    """Return candidate, or candidate with (N) suffix if it already exists."""
    if not candidate.exists():
        return candidate
    stem, ext = candidate.name.rsplit(".", 1)
    counter = 1
    while True:
        new = candidate.parent / f"{stem} ({counter}).{ext}"
        if not new.exists():
            return new
        counter += 1


def _resolve_single_out(
    src: pathlib.Path, out: pathlib.Path | None, fmt: str
) -> pathlib.Path:
    """Return the output path for a single-file extraction."""
    fmt_ext = _EXT_MAP[fmt]
    base = src.stem + "_" + src.suffix.lstrip(".") + fmt_ext
    if out is None:
        return _safe_path(pathlib.Path.cwd() / base)
    if out.is_dir():
        return _safe_path(out / base)
    #explicit file path — refuse if it exists, never overwrite
    if out.exists():
        raise click.ClickException(
            f"output file already exists: {out}\n"
            f"Hint: remove it first, or omit --out to use "
            f"collision-safe naming ({base})."
        )
    return out


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json", "text"], case_sensitive=False),
    default="markdown",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--out",
    "-o",
    type=click.Path(path_type=pathlib.Path),
    default=None,
    help=(
        "Output file or directory. "
        "Single-file default: write to CWD. "
        "Directory-mode default: ./extracted/ in CWD."
    ),
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Raise on unknown content and malformed present XML parts.",
)
@click.option(
    "--with-images",
    is_flag=True,
    default=False,
    help="Read and embed image binaries. Default skips binary reads; "
    "images are placeholders without this flag.",
)
@click.option(
    "--heading-detection",
    type=click.Choice(["auto", "structural", "none"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Heading detection strategy: auto (structural + font heuristic), "
    "structural (outline/style only), none (all paragraphs are BODY).",
)
@click.option(
    "--types",
    default=None,
    help=(
        "Comma-separated extensions to process in directory mode, e.g. hwpx,hwp. "
        "Default: all recognised Hancom extensions; unsupported formats are skipped."
    ),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Print per-file progress in directory mode.",
)
def extract(
    path: pathlib.Path,
    format: str,
    out: pathlib.Path | None,
    strict: bool,
    with_images: bool,
    heading_detection: str,
    types: str | None,
    verbose: bool,
) -> None:
    """Extract document content as markdown, json, or text.

    PATH may be a single file or a directory. Without --out, single-file
    mode writes to CWD; directory mode writes to ./extracted/.
    """
    fmt = format.lower()
    hd = cast(HeadingDetection, heading_detection)

    # --- single file ---
    if path.is_file():
        click.echo(f"Parsing {path.name}...", nl=False)
        t0 = time.monotonic()
        try:
            doc = openhanji.open(
                path, strict=strict, with_images=with_images, heading_detection=hd
            )
        except (openhanji.OpenHanjiError, FileNotFoundError) as exc:
            click.echo("")  # newline after "Parsing..."
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        output = _convert(doc, fmt)
        out_path = _resolve_single_out(path, out, fmt)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        elapsed = time.monotonic() - t0
        click.echo(f" Written to {out_path} ({elapsed:.1f}s)")
        return

    # --- directory mode ---
    out_root = out if out is not None else pathlib.Path.cwd() / "extracted"

    if types:
        exts = {"." + t.lstrip(".").lower() for t in types.split(",")}
        unknown = exts - _SUPPORTED_EXTENSIONS
        if unknown:
            click.echo(
                f"Error: unknown type(s): {', '.join(sorted(unknown))}. "
                f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}",
                err=True,
            )
            sys.exit(1)
    else:
        exts = _SUPPORTED_EXTENSIONS

    files = sorted(f for f in path.rglob("*") if f.suffix.lower() in exts)
    if not files:
        click.echo(f"No supported files found in {path}", err=True)
        sys.exit(1)

    out_root.mkdir(parents=True, exist_ok=True)

    # Mixed-type: more than one distinct extension -> per-type subfolders
    present_exts = {f.suffix.lower() for f in files}
    use_subfolders = len(present_exts) > 1

    succeeded = failed = skipped = 0
    fmt_ext = _EXT_MAP[fmt]

    disable_bar = verbose or not sys.stdout.isatty()
    with tqdm_mod.tqdm(
        files, unit="file", desc="Extracting", disable=disable_bar
    ) as bar:
        for file in bar:
            if verbose:
                click.echo(f"  {file.name}")
            try:
                doc = openhanji.open(
                    file, strict=strict, with_images=with_images, heading_detection=hd
                )
                output = _convert(doc, fmt)
                base = file.stem + "_" + file.suffix.lstrip(".") + fmt_ext
                if use_subfolders:
                    sub = out_root / file.suffix.lstrip(".")
                    sub.mkdir(exist_ok=True)
                    out_path = _safe_path(sub / base)
                else:
                    out_path = _safe_path(out_root / base)
                out_path.write_text(output, encoding="utf-8")
                succeeded += 1
                if verbose:
                    click.echo(f"  [ok] → {out_path.name}")
            except openhanji.NotSupportedError as exc:
                skipped += 1
                if verbose:
                    click.echo(f"  [skip] {file.name} [{exc}]", err=True)
            except (openhanji.OpenHanjiError, FileNotFoundError) as exc:
                failed += 1
                click.echo(f"  [error] {file.name} [{exc}]", err=True)

    click.echo(f"Done: {succeeded} succeeded, {failed} failed, {skipped} skipped")
    if failed:
        sys.exit(1)


main.add_command(extract)


def _convert(doc: HancomDocument, fmt: str) -> str:
    if fmt == "json":
        if not isinstance(doc, Document):
            raise openhanji.NotSupportedError(
                "JSON conversion is not implemented for this document type."
            )
        return to_json(doc)
    if fmt == "text":
        return doc.to_text()
    return doc.to_markdown()


@main.command()
@click.argument(
    "path",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path
    ),
)
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
    rows.extend(
        [
            ("Paragraphs", str(len(doc.paragraphs))),
            ("Tables", str(len(doc.tables))),
            ("Images", str(len(doc.images))),
        ]
    )
    width = max(len(k) for k, _ in rows)
    for key, val in rows:
        click.echo(f"  {key:<{width}}  {val}")
