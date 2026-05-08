# CLI

`openhanji` ships a `click`-based CLI with two subcommands: `extract`
and `info`. The entry point is registered as the `openhanji` console
script in `pyproject.toml`.

```bash
openhanji --help
openhanji --version       #also -v
```

## `extract`

Extract document content as Markdown, JSON, or plain text.

```
openhanji extract PATH [--format {markdown,json,text}] [--out PATH] [--strict] [--with-images] [--heading-detection {auto,structural,none}]
```

`PATH` may be **a single `.hwpx` file** or **a directory**. Directory
mode walks `PATH` recursively for `*.hwpx` and writes one output file
per input.

### Options

| Flag                   | Default     | Notes                                                                             |
| ---------------------- | ----------- | --------------------------------------------------------------------------------- |
| `--format`, `-f`       | `markdown`  | One of `markdown`, `json`, `text`. Case-insensitive.                              |
| `--out`, `-o`          | stdout      | Output file (single-file mode) **or** output directory (directory mode, required) |
| `--strict`             | off         | Raise on unknown XML content instead of skipping it.                              |
| `--with-images`        | off         | Read and embed image binaries. Without this flag images render as placeholders and no binary reads are performed. Has no effect with `-f text`. |
| `--heading-detection`  | `auto`      | Heading classification strategy: `auto` (structural signals + font heuristic), `structural` (outline level / style name only), `none` (all paragraphs forced to `BODY`). |

### Format choice

| `--format` | Output                                                                                              |
| ---------- | --------------------------------------------------------------------------------------------------- |
| `markdown` | GFM. Headings, simple tables as pipe tables, complex tables fall back to HTML `<table>`.            |
| `json`     | Full-fidelity tree. Run-level `bold`/`italic`/`font_size`/`color` are included only when non-default. |
| `text`     | Plain text. Tables flattened with tabs/newlines; nested tables included recursively.                  |

### Examples

```bash
# default markdown to stdout
openhanji extract document.hwpx

# JSON to a file
openhanji extract document.hwpx -f json -o document.json

# text format
openhanji extract document.hwpx --format text

# strict mode — unknown content raises CorruptedFileError / UnknownRecordError
openhanji extract document.hwpx --strict

# include image binaries (base64-inlined; omitted by default)
openhanji extract document.hwpx --with-images
openhanji extract document.hwpx -f json --with-images -o document.json

# heading detection — structural only (no font heuristic)
openhanji extract document.hwpx --heading-detection structural

# heading detection — disable entirely (all paragraphs become BODY)
openhanji extract document.hwpx --heading-detection none

# directory mode — convert every .hwpx under ./docs/ into ./out/
openhanji extract ./docs/ -o ./out/ -f markdown
```

In directory mode, output filenames are derived from input stems with
the format-specific extension (`.md`, `.json`, `.txt`). Existing files
are overwritten.

### Exit codes

- `0` — success.
- `1` — error (invalid path, no `.hwpx` files in directory mode, parse
  failure on at least one file). Per-file errors in directory mode are
  printed to stderr and the run continues; the process exits `1` if
  **any** file failed.

## `info`

Print metadata and body counts for a single document.

```bash
openhanji info document.hwpx
```

Output includes (when present): title, author, subject, keywords,
created/modified dates, page count, plus paragraph / table / image
counts. Empty fields are omitted from the printout.

Example output:

```
  Created     2024-01-15 10:23:45
  Modified    2024-03-02 18:09:11
  Paragraphs  90
  Tables      19
  Images      7
```

!!! tip "Empty title and author are normal"
    Most HWPX documents don't populate `<dc:title>` or
    `<dc:creator>`. If `info` doesn't print them, the document simply
    didn't include them — see [Quickstart › Read metadata](usage.md#read-metadata).
