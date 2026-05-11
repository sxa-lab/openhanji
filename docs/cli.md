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
openhanji extract PATH [--format {markdown,json,text}] [--out PATH] [--strict] [--with-images] [--heading-detection {auto,structural,none}] [--types EXTS] [--verbose]
```

`PATH` is **a single Hancom Office file** (`.hwpx`) or **a directory**.
Directory mode walks `PATH` recursively for recognised Hancom extensions
(`.hwpx`, `.hwp`, `.cell`, `.show`). In v0.1.0, only `.hwpx` is parsed;
`.hwp`, `.cell`, and `.show` inputs are reported as skipped until their
parsers are implemented.

### Options

| Flag                   | Default               | Notes                                                                             |
| ---------------------- | --------------------- | --------------------------------------------------------------------------------- |
| `--format`, `-f`       | `markdown`            | One of `markdown`, `json`, `text`. Case-insensitive.                              |
| `--out`, `-o`          | CWD / `./extracted/`  | Output file or directory. Single-file default: write to CWD. Directory-mode default: `./extracted/` in CWD. |
| `--strict`             | off                   | Raise on unrecognised document elements and malformed present XML parts instead of skipping or warning. |
| `--with-images`        | off                   | Read and embed image binaries. Without this flag images are placeholders and no binary reads are performed. Image binaries are not included in text output. |
| `--heading-detection`  | `auto`                | Heading classification strategy: `auto` (structural signals + font heuristic), `structural` (outline level / style name only), `none` (all paragraphs forced to `BODY`). |
| `--types`              | all                   | Comma-separated extensions to process in directory mode (e.g. `hwpx,hwp`). Defaults to all recognised Hancom extensions. Exits with an error if an unknown extension is supplied. Unsupported recognised formats are skipped. |
| `--verbose`, `-v`      | off                   | Print per-file `[ok]` / `[skip]` / `[error]` progress lines in directory mode instead of the tqdm bar.   |

### Format choice

| `--format` | Output                                                                                              |
| ---------- | --------------------------------------------------------------------------------------------------- |
| `markdown` | GFM. Headings, simple tables as pipe tables, complex tables fall back to HTML `<table>`.            |
| `json`     | Full-fidelity tree. Run-level `bold`/`italic`/`font_size`/`color` are included only when non-default. |
| `text`     | Plain text. Tables flattened with tabs/newlines; nested tables included recursively.                  |

### Examples

```bash
# single file — writes document_hwpx.md to CWD
openhanji extract document.hwpx

# single file — explicit output file
openhanji extract document.hwpx -f json -o document.json

# single file — place inside an existing directory
openhanji extract document.hwpx --out ./output/

# strict mode — unknown content and malformed present XML parts raise
openhanji extract document.hwpx --strict

# include image binaries (base64-inlined; placeholders by default)
openhanji extract document.hwpx --with-images
openhanji extract document.hwpx -f json --with-images -o document.json

# heading detection — structural only (no font heuristic)
openhanji extract document.hwpx --heading-detection structural

# heading detection — disable entirely (all paragraphs become BODY)
openhanji extract document.hwpx --heading-detection none

# batch — writes to ./extracted/ in CWD by default
openhanji extract ./docs/

# batch — explicit output directory
openhanji extract ./docs/ --out ./out/ -f markdown

# batch — filter to specific extensions; hwp is recognised but skipped in v0.1.0
openhanji extract ./docs/ --out ./out/ --types hwpx,hwp

# batch — per-file progress lines instead of tqdm bar
openhanji extract ./docs/ --out ./out/ --verbose
```

### Output placement

**Single file** — output goes to `--out` when given. If `--out` is an
existing directory, the file is placed inside it. If `--out` is omitted,
the file is written to CWD.

**Directory mode** — output root is `--out` when given, otherwise
`./extracted/` in CWD. When the input directory contains more than one
recognised file type, successful outputs are organised into per-type
subfolders (`hwpx/`, `hwp/`, `cell/`, `show/`). Same-type batches are written
flat. Unsupported recognised formats produce `[skip]` entries and no
output file.

**Output filenames** are `stem_ext.fmt` — e.g. `document.hwpx` becomes
`document_hwpx.md`. If that name already exists, a counter is appended:
`document_hwpx (1).md`, `document_hwpx (2).md`, and so on.

**Files are never overwritten.** Batch mode uses the collision counter
automatically. Single-file mode with an explicit `--out <file>` path
exits `1` if the target already exists — remove it first, or omit
`--out` to let collision-safe naming handle it.

### Progress output

- **Single file** — `Parsing <filename>... Written to <path> (Xs)` on one line.
- **Batch** — silent by default. Use `--verbose` to see per-file `[ok]` / `[skip]` / `[error]` lines as files are processed.
- **Summary** — always printed after a batch run:
  `Done: N succeeded, N failed, N skipped`.

### Exit codes

- `0` — success. In batch mode: all files succeeded or were skipped as unsupported.
- `1` — fatal error before processing began (invalid path, no supported
  files found in directory mode, parse failure in single-file mode), **or**
  at least one file failed in a batch run. In batch mode the run always
  completes — failed files are logged to stderr and counted, then the
  exit code reflects the final tally.

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
    `<dc:creator>`. If `info` doesn't print them, the document
    didn't include them — see [Quickstart › Read metadata](usage.md#read-metadata).
