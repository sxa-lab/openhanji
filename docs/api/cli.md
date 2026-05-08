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
mode — the dispatch is on `path.is_dir()`.

### Single-file mode

When `path` is a file:

1. Open the document via `openhanji.open(path, strict=strict, with_images=with_images)`.
2. Render via [`_render`](#_render) to the target format.
3. If `--out` is given, write to that file. Otherwise echo to stdout.

`OpenHanjiError` and `FileNotFoundError` are caught, printed to
stderr with the `Error:` prefix, and the process exits `1`.

### Directory mode

When `path` is a directory:

1. `--out` is **required** (an output directory). The command exits
   `1` with `Error: --out is required when PATH is a directory.` if
   missing.
2. Create the output directory if needed (`mkdir(parents=True, exist_ok=True)`).
3. Walk `path` recursively for `*.hwpx` (sorted, for deterministic
   output ordering). Exit `1` with `No .hwpx files found in <path>`
   if the walk finds nothing.
4. For each file, parse and render. Per-file failures are printed to
   stderr (`Error [<filename>]: <message>`) and the run continues.
5. If **any** file failed, exit `1` after processing all files.
   Otherwise exit `0`.

Output filenames are derived as `<input-stem><format-extension>` using
`_EXT_MAP`:

```python
_EXT_MAP = {"markdown": ".md", "json": ".json", "text": ".txt"}
```

So `document.hwpx` with `--format markdown` produces `document.md` in the
output directory. Existing files with the same name are overwritten.

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

## `_render`

::: openhanji.cli._render
    options:
      show_root_heading: false

Internal dispatch helper that maps the `--format` string to the
corresponding `Document` method. Not part of the public API; documented
here so contributors can wire new formats in one place.

```python
def _render(doc, fmt):
    if fmt == "json":
        return doc.to_json()
    if fmt == "text":
        return doc.to_text()
    return doc.to_markdown()    # default
```

## `_EXT_MAP`

The format → extension mapping used in directory mode. Keep it in
sync with the `--format` `click.Choice` and `_render`.

```python
_EXT_MAP = {"markdown": ".md", "json": ".json", "text": ".txt"}
```
