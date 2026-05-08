# Parsers

The parser layer turns a file on disk into a [`Document`](document.md#document).

For most users, [`openhanji.open()`](openhanji.md#open) is all you need —
it dispatches to the correct parser and returns the document. The
classes here are documented for contributors and embedders who need
to drive parsing directly (e.g. running multiple parsers in parallel
threads, or providing a pre-opened file handle).

## `BaseParser`

::: openhanji.parsers.base.BaseParser

The ABC for all format-specific parsers. The contract is intentionally
narrow:

- `__init__(self, strict: bool = False, with_images: bool = False, heading_detection: str = "auto")` —
  accepts the strict, with_images, and heading_detection flags.
- `parse(self, path: pathlib.Path) -> Document` — parses the file at
  `path` and returns a `Document`. Must raise an
  [`OpenHanjiError`](exceptions.md#openhanjierror) subclass on
  recoverable failure; system-level errors (e.g. `OSError`, broken
  zip) may propagate unwrapped.

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
`header.xml`, then walks every `section*.xml` in numeric order
(`section0.xml`, `section1.xml`, …, **not** lexicographic, so
`section10.xml` correctly comes after `section9.xml`).

### Pipeline

1. **Open the zip.** Raise [`CorruptedFileError`](exceptions.md#corruptedfileerror)
   if the file is not a valid zip or required parts are missing.
2. **Read `content.hpf`** for OPF metadata: title (`<opf:title>`),
   author (`<opf:meta name="creator">`), subject (`<opf:meta name="subject">`),
   dates, and keywords (split on commas and newlines).
3. **Read `header.xml`** for Dublin Core (`<dc:title>`, `<dc:creator>`,
   `<dc:subject>`) as a fallback when `content.hpf` leaves those fields
   empty. Also builds the [`HeaderIndex`](#headerindex):
   font face table, char shapes table, para shapes table, styles table.
4. **Walk sections** in numeric order. For each `<hp:p>`, build a
   `Paragraph`, group consecutive `<hp:t>` nodes into `Run` objects
   keyed by `charPrIDRef`, attach character formatting from the
   `charPr` index, and resolve paragraph style/alignment from the
   `paraPr` and styles indices. Paragraph style detection runs four
   paths in order: `hh:heading` child element → `outlineLevel`
   attribute → styleIDRef name → font heuristic (display font face +
   size threshold, short paragraphs only).
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
being skipped with a `WARNING` log. Malformed XML, missing required
parts, and zip-level errors raise
[`CorruptedFileError`](exceptions.md#corruptedfileerror) regardless of
the strict flag.

---

## Internal helpers

These are not public API — their signatures may change without a
major version bump. Documented here for contributors.

### `HeaderIndex`

::: openhanji.parsers.hwpx.HeaderIndex

A bundle of lookup tables built once per document from `header.xml`:

- `font_faces` — `id → {hangul, latin, hanja, …}` font face metadata.
- `char_shapes` — `charPrID → CharShape` character formatting.
- `para_shapes` — `paraPrID → ParaShape` paragraph formatting (`outline_level`, `list_kind`, `align`).
- `styles` — `styleID → name` named-style table.

The walker holds a `HeaderIndex` and consults it for every `<hp:p>`
and `<hp:run>`. Building it once up-front avoids repeated XML scans.

### `CharShape`

::: openhanji.parsers.hwpx.CharShape

The denormalised character formatting record indexed by `charPrID`.
Mirrors the [`Run`](document.md#run) formatting fields exactly —
copying `CharShape` attributes onto a `Run` is the parser's hot path.
Carries both `font_face` (Hangul) and `font_face_latin` (Latin/ASCII),
resolved from the `refList` font face table in `header.xml`.

### `ParaShape`

::: openhanji.parsers.hwpx.ParaShape

The denormalised paragraph formatting record indexed by `paraPrID`.
Holds the three fields the walker needs per paragraph: `outline_level`
(maps to heading depth), `list_kind` (`"ordered"` / `"unordered"` /
`""`), and `align` (`"left"` / `"center"` / `"right"` / `"justify"` /
`""`).

`outline_level` is resolved with a preference order: a
`<hh:heading type="OUTLINE" level="N">` child element on `<hh:paraPr>`
takes precedence over the `outlineLevel` attribute. The child element
is the more explicit structural signal; the attribute is the fallback
for older documents that don't include it.
