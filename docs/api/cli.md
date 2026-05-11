# CLI internals

This page documents the Python entry points behind the `openhanji`
console script. End-user CLI usage lives on the [CLI](../cli.md) page.

The CLI is built with [`click`](https://click.palletsprojects.com/),
registered as the `openhanji` entry point in `pyproject.toml`:

```toml
[project.scripts]
openhanji = "openhanji.cli:main"
```

## `main`

::: openhanji.cli.main

The top-level `click.Group`. Holds the `--version` / `-v` option and
dispatches to the `extract` and `info` subcommands. You can re-use it
in a parent CLI by importing and adding it as a subgroup:

```python
import click
import openhanji.cli

@click.group()
def my_tool():
    pass

my_tool.add_command(openhanji.cli.main, name="hwpx")
```

After this, `my-tool hwpx extract …` works exactly like
`openhanji extract …`.

## `extract`

::: openhanji.cli.extract

The `extract` subcommand. Handles both single-file and directory
mode — the dispatch is on `path.is_file()`.

### Single-file mode

When `path` is a file:

1. Print `Parsing <filename>...` (no newline) and start a timer.
2. Open the document via `openhanji.open(path, strict=strict, with_images=with_images, heading_detection=hd)`.
3. Convert the document via [`_convert`](#_convert) to the target format string.
4. Resolve the output path via [`_resolve_single_out`](#_resolve_single_out).
5. Write the converted content to that path and print ` Written to <path> (Xs)` — completing the line started in step 1.

`OpenHanjiError` and `FileNotFoundError` are caught, a newline is
emitted to close the `Parsing…` line, the error is printed to stderr,
and the process exits `1`.

### Directory mode

When `path` is a directory:

1. Resolve the output root: `--out` if given, otherwise `./extracted/`
   in CWD. Create it with `mkdir(parents=True, exist_ok=True)`.
2. Resolve the extension filter: if `--types` is given, parse the
   comma-separated list into a set of dotted extensions (e.g. `hwpx,hwp`
   becomes `{".hwpx", ".hwp"}`). Unknown extensions exit `1` immediately.
   Otherwise the full `_SUPPORTED_EXTENSIONS` set is used.
3. Walk `path` recursively for files whose suffix matches the extension
   filter (sorted, for deterministic output ordering). Exit `1` with
   `No supported files found in {path}` if the walk finds nothing.
4. Determine subfolder mode: if the filtered file list contains more
   than one distinct extension, `use_subfolders = True` — successful output is
   organised into per-type subdirectories (`hwpx/`, `hwp/`, `cell/`, `show/`).
   Same-type batches are written flat.
5. Iterate with a tqdm progress bar (`unit="file"`, `desc="Extracting"`).
   The bar is disabled (`disable=verbose or not sys.stdout.isatty()`) —
   suppressed when `--verbose` is set or when stdout is not a TTY (CI,
   pipes). Per-file `[ok]` / `[skip]` / `[error]` lines are printed
   instead when `--verbose` is active.
   `NotSupportedError` increments `skipped`; other `OpenHanjiError` /
   `FileNotFoundError` increments `failed` and prints to stderr. The
   run continues after any per-file failure.
6. Print `Done: N succeeded, N failed, N skipped`.
7. Exit `1` if any file failed, `0` if all succeeded or were only skipped.
   The run always completes — no early exit on per-file failures.

Output filenames are `stem_ext.fmt` — e.g. `document.hwpx` with
`--format markdown` produces `document_hwpx.md`. If that name already
exists, [`_safe_path`](#_safe_path) appends a counter:
`document_hwpx (1).md`, `document_hwpx (2).md`, and so on. No files are
ever silently overwritten in batch mode.

## `info`

::: openhanji.cli.info

Prints metadata and body counts. Doesn't accept a `--format` flag —
output is always the human-readable two-column format.

Field rows are emitted only when the underlying value is set:

- `Title` if `metadata.title`
- `Author` if `metadata.author`
- `Subject` if `metadata.subject`
- `Keywords` if `metadata.keywords` (joined with `, `)
- `Created` if `metadata.created_at`
- `Modified` if `metadata.modified_at`
- `Pages` if `metadata.page_count is not None`

Body counts are **always** emitted:

- `Paragraphs`
- `Tables`
- `Images`

Counts come from the top-level `doc.paragraphs` / `doc.tables` /
`doc.images` filtered views, so they reflect the **top level only** —
nested tables and images inside table cells are not counted. This
matches the `doc.blocks` semantics described in the
[Document model](document.md#body-ordering) page.

The label column is right-padded to the longest label width for
alignment.

## `_convert`

::: openhanji.cli._convert
    options:
      show_root_heading: false

Internal dispatch helper that maps the `--format` string to the
corresponding converter and returns the document as a string. Not part
of the public API; documented here so contributors can wire new formats
in one place.

```python
def _convert(doc, fmt):
    if fmt == "json":
        if not isinstance(doc, Document):
            raise NotSupportedError("JSON conversion is not implemented for this document type.")
        return to_json(doc)
    if fmt == "text":
        return doc.to_text()
    return doc.to_markdown()    # default
```

`json` requires a concrete `Document` instance because `to_json()` is a
`Document`-specific converter, not part of the `HancomDocument` protocol.
Passing a non-`Document` object (e.g. from a future `.cell` parser) raises
`NotSupportedError` before any serialisation is attempted.

## `_resolve_single_out`

Internal helper that resolves the output path for single-file mode.
Four cases:

| `--out` value | Behaviour |
|---------------|-----------|
| Not given | Write `stem_ext.fmt` to CWD via `_safe_path` |
| Existing directory | Place `stem_ext.fmt` inside it via `_safe_path` |
| Explicit file path, doesn't exist | Write to that exact path |
| Explicit file path, already exists | `ClickException`, exit `1` — with hint to use collision-safe naming |

## `_safe_path`

Accepts a candidate `pathlib.Path`. Returns it unchanged if it doesn't
exist, otherwise appends ` (N)` before the extension and increments
until a free name is found:

```
document_hwpx.md → document_hwpx (1).md → document_hwpx (2).md → …
```

Used in both single-file and batch branches to prevent silent overwrites
on auto-placed output.

## `_EXT_MAP`

The format-to-extension mapping used in directory mode. Keep it in
sync with the `--format` `click.Choice` and `_convert`.

```python
_EXT_MAP = {"markdown": ".md", "json": ".json", "text": ".txt"}
```
