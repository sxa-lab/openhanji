# Parsers

The parser layer turns a file on disk into a `HancomDocument`.

For most users, [`openhanji.open()`](openhanji.md#open) is all you need —
it dispatches to the correct parser and returns the document. The
classes here are documented for contributors and embedders who need
to drive parsing directly (e.g. running multiple parsers in parallel
threads, or providing a pre-opened file handle).

## `HancomDocument`

::: openhanji.parsers.base.HancomDocument

A `@runtime_checkable` `Protocol` satisfied by every document model
returned by `openhanji.open()`. It is the declared return type of
`openhanji.open()` and `BaseParser.parse()`.

Importable directly from the top-level package:

```python
import openhanji

doc = openhanji.open("file.hwpx")
assert isinstance(doc, openhanji.HancomDocument)   # True at runtime
```

The protocol guarantees these members on every returned document:

| Member           | Type                          | Notes                                                              |
| ---------------- | ----------------------------- | ------------------------------------------------------------------ |
| `metadata`       | [`HancomMetadata`](#hancommetadata) | Title, author, dates, keywords, page count.                  |
| `paragraphs`     | `Sequence[object]`            | All paragraphs, flattened across sections.                         |
| `tables`         | `Sequence[object]`            | All top-level tables, flattened across sections.                   |
| `images`         | `Sequence[object]`            | All top-level image refs, flattened across sections.               |
| `to_markdown()`  | `str`                         | GFM output.                                                        |
| `to_text()`      | `str`                         | Plain text output.                                                 |

`to_json()` is **not** part of the protocol — it is a standalone
converter function (`openhanji.converters.json.to_json()`) that accepts
a `Document` instance.

---

## `HancomMetadata`

::: openhanji.parsers.base.HancomMetadata

A `@runtime_checkable` `Protocol` satisfied by every metadata object
on a `HancomDocument`. Accessed via `doc.metadata`.

| Property      | Type                  | Notes                                                         |
| ------------- | --------------------- | ------------------------------------------------------------- |
| `title`       | `str \| None`         | Document title from OPF / Dublin Core. Commonly `None`.       |
| `author`      | `str \| None`         | Creator field. Often the OS username.                         |
| `subject`     | `str \| None`         | Subject / description field.                                  |
| `keywords`    | `Sequence[str]`       | Keywords split on commas and newlines. Empty list when absent.|
| `created_at`  | `datetime \| None`    | Creation timestamp from `content.hpf`.                        |
| `modified_at` | `datetime \| None`    | Last-modified timestamp from `content.hpf`.                   |
| `page_count`  | `int \| None`         | Page count from `content.hpf`. `None` when absent.            |

---

## `HeadingDetection`

`HeadingDetection = Literal["auto", "structural", "none"]`

Importable from `openhanji.parsers.base`. Accepted by `openhanji.open()`,
`BaseParser.__init__()`, and `HwpxParser`. Controls how the parser
classifies paragraph styles:

| Value          | Behaviour                                                                                     |
| -------------- | --------------------------------------------------------------------------------------------- |
| `"auto"`       | Structural signals first (`outlineLevel`, style name), then font/size heuristic as fallback.  |
| `"structural"` | Structural signals only; font heuristic is skipped.                                           |
| `"none"`       | All paragraphs are forced to `BODY` — no heading detection at all.                            |

---

## `BaseParser`

::: openhanji.parsers.base.BaseParser

The ABC for all format-specific parsers. The contract is intentionally
narrow:

- `__init__(self, strict: bool = False, with_images: bool = False, heading_detection: str = "auto")` —
  accepts the strict, with_images, and heading_detection flags.
- `parse(self, path: pathlib.Path) -> HancomDocument` — parses the
  file at `path` and returns a `HancomDocument`. Must raise an
  [`OpenHanjiError`](exceptions.md#openhanjierror) subclass on
  failure; `HwpxParser` wraps unexpected exceptions as
  `CorruptedFileError`.

`strict`, `with_images`, and `heading_detection` are stored on `self`
and read by subclasses. `with_images=False` (the default) skips all
binary reads from the zip. `heading_detection` is typed as
`HeadingDetection = Literal["auto", "structural", "none"]`
(importable from `openhanji.parsers.base`). Validation happens in
`openhanji.open()` before the parser is instantiated.

### Adding a new parser

1. Subclass `BaseParser`.
2. Implement `parse()`.
3. Wire dispatch into `openhanji.open()` by adding the extension to
   the supported set and lazily importing the parser class.

The v0.2 plan for `.hwp` binary support follows exactly this shape.

---

## `HwpxParser`

::: openhanji.parsers.hwpx.HwpxParser

The HWPX implementation. Opens the HWPX as a zip, indexes
`header.xml`, then walks sections in the OPF spine order declared by
`content.hpf`. Spine hrefs are resolved against both the zip root and
the `content.hpf` directory because Hancom-saved files appear in both
forms; non-section spine entries such as `header.xml` are ignored. If
the package has no usable section spine, it falls back to numeric
filename order (`section0.xml`, `section1.xml`, …, **not**
lexicographic, so `section10.xml` correctly comes after `section9.xml`).
Package/header indexing lives in the internal `openhanji.parsers.hwpx_index`
module; document XML walking and block construction stay in
`openhanji.parsers.hwpx`.

### Pipeline

1. **Open the zip.** Raise [`CorruptedFileError`](exceptions.md#corruptedfileerror)
   if the file is not a valid zip.
2. **Read `header.xml`** for title, creator/author, and subject —
   Dublin Core fields, matched by local element name after namespace
   stripping. Also builds the `HeaderIndex`: font face
   table, char shapes table, para shapes table, styles table.
   `header.xml` is read first because it is more reliably populated in
   Hancom-saved files than `content.hpf`, even though the OWPML model
   (`hancom-io/hwpx-owpml-model`) designates `content.hpf` as the
   canonical OPF metadata location.
3. **Read `content.hpf`** for OPF metadata: title (`<opf:title>`),
   author (`<opf:meta name="creator">`), subject (`<opf:meta name="subject">`),
   dates, and keywords (split on commas and newlines). Title, author,
   and subject from `content.hpf` fill in only if `header.xml` left
   those fields empty — `header.xml` wins when both have a value.
4. **Walk sections** in OPF spine order, or numeric filename order when
   no usable section spine exists. For each `<hp:p>`, build a `Paragraph`,
   group consecutive `<hp:t>` nodes into `Run` objects
   keyed by `charPrIDRef`, attach character formatting from the
   `charPr` index, and resolve paragraph style/alignment from the
   `paraPr` and styles indices. Paragraph style detection runs four
   paths in order: `heading` child element, then `outlineLevel`
   attribute, then styleIDRef name matching a heading pattern, then
   font heuristic (display font face + size threshold, short paragraphs only).
5. **Inline tables and images.** OWPML allows `<hp:tbl>` and
   `<hp:pic>` to appear inline inside `<hp:p><hp:run>`. The walker
   emits these as separate top-level `Table` / `ImageRef` nodes at
   their position in document order.
6. **Extract headers and footers.** `ctrl > header` / `ctrl > footer`
   elements are walked for their `subList > p` paragraphs. Header and
   footer paragraphs are stored per-section on `Section.headers` /
   `Section.footers`; `Document.headers` / `Document.footers` flatten
   across all sections.
7. **Produce one `Section` per `section*.xml` file**, storing blocks,
   headers, footers, section index, and source path. The parser returns
   a `list[Section]` which `Document` stores on `doc.sections`.
8. **Resolve image binaries** via `binaryItemIDRef` against `BinData/`
   parts in the zip. Skipped entirely when `with_images=False`.

### Skip lists

Two named skip sets control what the walker ignores:

- **`_SKIP_TAGS`** — layout-only elements that contribute no
  extractable text or structure (line segments, char/para shape
  references, page numbers, cell geometry, drawing transforms, …).
  Recursive descent stops at these.
- **`_SPACE_TAGS`** — elements that contribute a single space when
  flattening cell text (`tab`, `nbSpace`, `fwSpace`).
- **`_HEADING_FONT_FACES`** — Korean display font faces used as a
  heading signal by the font heuristic (`HY헤드라인M`, `HY헤드라인B`,
  `HY울릉도M`, `HY견고딕`, `바탕`). Extend this set when you encounter
  documents that use other dedicated display fonts for headings.
- **`_BODY_FONT_FACES`** — fonts that are always body text regardless
  of size or bold (`맑은 고딕`). Takes precedence over `_HEADING_FONT_FACES`
  and the size/bold thresholds — the heuristic returns `None` immediately
  for any paragraph whose dominant font is in this set.

`ctrl` elements are walked for `header` / `footer` children. Other
ctrl content — `fieldBegin`, `fieldEnd`, `colPr`, `pageNum` — is in
`_SKIP_TAGS` and carries no extractable text.

### Strict mode behaviour

When `self.strict` is `True`, unrecognised top-level elements raise
[`UnknownRecordError`](exceptions.md#unknownrecorderror) instead of
being skipped with a `WARNING` log. Malformed present XML parts
(`header.xml`, `content.hpf`, or section XML) raise
[`CorruptedFileError`](exceptions.md#corruptedfileerror). Missing optional
metadata/header parts remain allowed. Zip-level errors raise
[`CorruptedFileError`](exceptions.md#corruptedfileerror) in both modes.
