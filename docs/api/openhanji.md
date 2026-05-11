# `openhanji`

The top-level package. Import everything you need directly from `openhanji`:

```python
import openhanji

doc = openhanji.open("document.hwpx")

# All model types are re-exported at the top level
para: openhanji.Paragraph
run: openhanji.Run
cell: openhanji.Cell
style: openhanji.ParagraphStyle
```

Re-exported names: `open`, `Document`, `HancomDocument`, `Section`, `Paragraph`, `Run`, `Table`, `Row`,
`Cell`, `ImageRef`, `Metadata`, `ParagraphStyle`, `OpenHanjiError`,
`NotSupportedError`, `CorruptedFileError`, `UnknownRecordError`.

## `open()`

::: openhanji.open
    options:
      show_root_heading: false

### What it does

`openhanji.open()` is the **only** place format dispatch lives in the
package. It:

1. Resolves `path` to a `pathlib.Path` and verifies it exists
   (raises `FileNotFoundError` if not — note: this is the standard
   library exception, **not** an `OpenHanjiError` subclass).
2. Lower-cases the suffix and dispatches on it — `.hwpx` goes to
   `HwpxParser`; `.hwp`, `.cell`, `.show` raise `NotSupportedError`
   with a "Coming soon!" message; anything else raises `NotSupportedError`
   with a generic unsupported-format message.
3. Lazily imports `HwpxParser`, instantiates it with `strict`,
   `with_images`, and `heading_detection`, and returns `parser.parse(path)`.

### `with_images=True` — opt in to image binaries

By default, `openhanji.open()` **skips all binary reads** from the
HWPX zip. `ImageRef` nodes are still present in the document at their
correct positions, but `img.data` is `None` and `img.format` is `None`.
Markdown output renders `![caption](image_N)` placeholders; JSON
emits `"data": null`.

Pass `with_images=True` to read and attach the binaries:

```python
doc = openhanji.open("document.hwpx", with_images=True)
# img.data is bytes, img.format is "png" / "jpg" / etc.
```

For image-heavy documents the default path is significantly faster —
no zip decompression happens for any `BinData/` entry.

### `heading_detection` — control heading inference

Three modes, passed as a string:

| Value          | Behaviour                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------ |
| `"auto"`       | Default. Structural signals first (outline level, style name), then font heuristic.             |
| `"structural"` | Structural signals only. Font heuristic disabled. Safe for well-structured documents.            |
| `"none"`       | **Disables all heading detection** — both structural signals and the font heuristic. Every paragraph is `BODY`. Use when you want raw text with no heading classification at all. |

`"none"` is not "no heuristic only" — it also ignores `outlineLevel`
and style-name heading signals. Use `"structural"` if you want to keep
the explicit structural markers while suppressing the heuristic.

```python
# structural only — no font heuristic, but outlineLevel still respected
doc = openhanji.open("document.hwpx", heading_detection="structural")

# all BODY — no heading detection at all
doc = openhanji.open("document.hwpx", heading_detection="none")
```

An invalid value raises `ValueError` immediately, before the file is opened.

### When to use `strict=True`

Default behaviour (`strict=False`) is tolerant: unknown XML elements
are skipped and logged at `WARNING`. This is the right mode for batch
ingestion across arbitrary HWPX files, where one unusual document
should not stop the whole run.

Use `strict=True` when unsupported content should fail the parse:

- Test suites validating known-good documents.
- Validation jobs where unrecognised content indicates a bug.
- Tests that need to catch unsupported content immediately.

In strict mode, unknown XML raises
[`UnknownRecordError`](exceptions.md#unknownrecorderror). Malformed
present XML parts (`header.xml`, `content.hpf`, or section XML) raise
[`CorruptedFileError`](exceptions.md#corruptedfileerror). Missing optional
metadata/header parts are still allowed. Both parser errors inherit from
[`OpenHanjiError`](exceptions.md#openhanjierror), so a single
`except OpenHanjiError:` catches every parser-level failure.

### Exception hierarchy

```
FileNotFoundError                # path doesn't exist (stdlib)
OpenHanjiError                   # base for everything below
├── NotSupportedError            # unsupported extension (e.g. .hwp in v0.1)
├── CorruptedFileError           # malformed zip / malformed present XML part
└── UnknownRecordError           # strict mode: unrecognised XML element
```

### Examples

```python
import openhanji

# default: skip unknown content, return whatever parsed cleanly
doc = openhanji.open("document.hwpx")

# strict: any surprise is fatal
try:
    doc = openhanji.open("document.hwpx", strict=True)
except openhanji.UnknownRecordError as e:
    log.error("unrecognised HWPX content: %s", e)
except openhanji.OpenHanjiError as e:
    log.error("parse failed: %s", e)
```

## `__version__`

The installed package version, as a string. Mirrors the
`pyproject.toml` `[project] version` field. Use it for diagnostics or
to gate version-specific behaviour in downstream code.

```python
>>> import openhanji
>>> openhanji.__version__
'0.1.0'
```
