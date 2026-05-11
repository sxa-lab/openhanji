# Document model

Plain dataclasses, no ORM, no magic. Everything in
`openhanji.models.document` is a simple value object you can pickle, copy,
or serialise. All composite nodes have a `to_dict()` method used by
[`openhanji.converters.json.to_json()`](converters.md#to_json).

## `Document`

::: openhanji.models.document.Document

`Document` is constructed in one of two ways:

```python
# Structured — one Section per source XML file, as the parser produces:
doc = Document(sections=[Section(blocks=[...], index=0, source_path="Contents/section0.xml")])

# Flat convenience — wraps a block list into a single anonymous Section:
doc = Document(body=[Paragraph(text="hello"), Table()])
```

Both produce the same flattened views. Use `body=` for one-section
documents and tests; use `sections=` when you need per-section
metadata (page headers/footers, source paths).

### Sections

`doc.sections` is the canonical store — a list of [`Section`](#section)
objects, one per source XML file. The parser builds one `Section` per
section file it walks, using usable `section*.xml` entries from OPF
spine order when available and numeric filename order as the fallback.

The flattened properties (`doc.paragraphs`, `doc.tables`, `doc.images`,
`doc.headers`, `doc.footers`) iterate across **all** sections. They are
the right tool for document-wide queries.

### Body ordering

`doc.blocks` is a flat, **ordered** list of all `Paragraph`, `Table`,
and `ImageRef` nodes across all sections, in document order. This is
the public property converters use to iterate the document.

`blocks` only holds **top-level** items. Tables and images nested
inside table cells are stored on `Cell.blocks` and do **not** appear
in `doc.blocks`, `doc.tables`, or `doc.images`. Use `cell.blocks` (or
`cell.tables` / `cell.images`) for nested traversal.

### Headers and footers

`doc.headers` and `doc.footers` are `list[Paragraph | Table | ImageRef]`
flattened across all sections. Most page headers/footers contain only
paragraphs, but Hancom documents can include tables and images in
header/footer regions — those are preserved here too.

```python
for block in doc.headers:
    if isinstance(block, Paragraph):
        print(block.text)

for block in doc.footers:
    if isinstance(block, Paragraph):
        print(block.text)
```

In flat JSON output (`mode="flat"`, the default), `"headers"` and
`"footers"` keys are present only when non-empty. In structured JSON
(`mode="structured"`), headers/footers appear per section inside each
section dict, also omitted when empty. In Markdown output, paragraph
texts are joined with ` | ` and emitted as an HTML comment
(`<!-- header: text -->`); non-Paragraph blocks in the header/footer
region are silently dropped by the converter. In plain text, the same
join applies and they render as `[header: text]` / `[footer: text]`
lines.

### JSON conversion

JSON conversion is provided by
[`openhanji.converters.json.to_json()`](converters.md#to_json).
Default formatting fields on runs are **omitted** from the output — this keeps payloads compact
and signals "default formatting" by absence rather than by explicit
`false` / `null`.

```python
import openhanji
from openhanji.converters.json import to_json

doc = openhanji.open("document.hwpx")
print(to_json(doc, indent=2))
```

Two output shapes, controlled by the `mode` kwarg:

The `mode` parameter is typed as `JsonMode = Literal["flat", "structured"]`
(importable from `openhanji.converters.json`). Any other value raises
`ValueError` before serialisation begins.

**`mode="flat"` (default)** — single flat `"body"` list, best for RAG/NLP:

```json
{
  "metadata": { "title": null, "author": null, ... },
  "body": [
    {"type": "paragraph", "index": 0, "style": "HEADING1", "level": 0, "text": "...", "runs": [...]},
    {"type": "table", "index": 0, "rows": [...], "caption": null},
    {"type": "image", "index": 0, "format": null, "data": null}
  ]
}
```

**`mode="structured"`** — one object per source section, preserves section
boundaries and per-section headers/footers:

```json
{
  "metadata": { ... },
  "sections": [
    {
      "index": 0,
      "source_path": "Contents/section0.xml",
      "blocks": [...],
      "headers": [...],   //omitted when empty
      "footers": [...]    //omitted when empty
    }
  ]
}
```

By default `"data"` on image nodes is `null` — binaries are not read
from the zip. Pass `with_images=True` to `openhanji.open()` to get
base64-inlined binaries instead.

### `to_markdown()` / `to_text()` / `to_json()`

Converts the document using [`openhanji.converters.markdown`](converters.md#to_markdown),
[`openhanji.converters.text`](converters.md#to_text), and
[`openhanji.converters.json`](converters.md#to_json) respectively.
See the [converters page](converters.md) for the full rendering rules.

---

## `Section`

::: openhanji.models.document.Section

A `Section` maps 1:1 to one `section*.xml` file in the HWPX zip.
It holds all blocks from that file, plus the page-level headers and
footers extracted from its `ctrl > header` / `ctrl > footer` elements.

```python
for section in doc.sections:
    print(f"section {section.index} ({section.source_path})")
    for block in section.blocks:
        ...
```

The filtered views on `Section` (`section.paragraphs`, `section.tables`,
`section.images`) work the same as on `Document` but are scoped to that
single section. `section.headers` / `section.footers` are
`list[Paragraph | Table | ImageRef]` holding all blocks extracted from
the header/footer regions of **this** section's pages.

`source_path` is a string like `"Contents/section0.xml"`. It is `None`
when the `Section` was constructed directly (e.g. in tests via
`Document(body=[...])`).

### `Section.to_dict()` output

`section.to_dict()` is the building block for `mode="structured"` JSON.
Its output shape:

```json
{
  "index": 0,
  "source_path": "Contents/section0.xml",
  "blocks": [...],
  "headers": [...],   // omitted when empty
  "footers": [...]    // omitted when empty
}
```

`"headers"` and `"footers"` are omitted when empty. `"blocks"` is a
list of paragraph / table / image dicts (same shape as `mode="flat"`
body items). `"source_path"` is `null` for `Section` objects created
without one (e.g. via `Document(body=[...])`).

---

## `Paragraph`

::: openhanji.models.document.Paragraph

### Field semantics

- **`text`** — the exact concatenation of all run texts, including any
  leading or trailing whitespace the source encodes as indentation.
  `paragraph.text == "".join(r.text for r in paragraph.runs)` holds
  whenever `runs` is non-empty — enforced by `__post_init__`.
  For RAG chunking use `paragraph.text.strip()`; for character-level
  formatting use `runs`.
- **`style`** — a [`ParagraphStyle`](#paragraphstyle) enum value.
  Defaults to `BODY`. Heading levels 1–6 set both `style` and `level`.
- **`level`** — depth for headings and lists. `0` for body text.
  Lists use `level` for nesting depth (Markdown converter renders
  `'  ' * level` indentation).
- **`runs`** — list of [`Run`](#run) objects in source order. May be
  empty for purely structural paragraphs (e.g. an empty paragraph
  used as vertical spacing).
- **`index`** — zero-based position in `Document.blocks` (shared
  counter across paragraphs, tables, and images). Stable across runs
  of the parser.
- **`align`** — alignment string from `paraPr` when resolvable
  (`"left"`, `"center"`, `"right"`, `"justify"`). `None` when the
  paragraph inherits or no `paraPr` reference resolves.
- **`style_name`** — named style from the styles table in
  `header.xml` (e.g. `"본문"`, `"개요1"`). `None` when not resolved.

### JSON serialisation

`align` and `style_name` are **omitted** when `None`. `runs` is always
emitted (possibly as `[]`). The `type: "paragraph"` discriminator
identifies the node when reading back from JSON.

---

## `Run`

::: openhanji.models.document.Run

### Field semantics

A `Run` is a contiguous span of text within a paragraph that shares
character formatting. The HWPX parser groups consecutive `<hp:t>`
text nodes pointing to the same `charPrIDRef` into one `Run`.

- **`text`** — the literal characters. Contains newlines where the
  source has `<hp:lineBreak>` and spaces for `<hp:tab>` /
  `<hp:nbSpace>` / `<hp:fwSpace>`.
- **`bold`**, **`italic`**, **`underline`** — character flags. Defaults
  to `False`. Underline is preserved in the model and JSON but only
  rendered in HTML output (Markdown has no native underline syntax).
- **`font_size`** — points, as a float. `None` means "inherit
  paragraph default."
- **`color`** — hex string, e.g. `"#FF0000"`. `None` means the run
  inherits the default color. The parser does not normalise to
  lowercase or validate the hex.
- **`font_face`** — Hangul font face resolved from the `header.xml`
  `refList` font face table via the run's `charPrIDRef`. `None` when
  the reference is absent or doesn't resolve.
- **`href`** — URL string when the run is inside a `HYPERLINK` field
  span (`fieldBegin[type=HYPERLINK]`). `None` for all other runs.
  Populated from the `Path` parameter of the field. Present in JSON
  output only when set; renders as `[text](url)` in Markdown and
  `<a href="...">` in HTML table cells.

### JSON serialisation is sparse

Default-valued fields are dropped from `to_dict()` output. A run with
no formatting serialises as `{"text": "..."}`. This is
intentional — most runs have no formatting, so
omitting defaults keeps the JSON 3–5× smaller without losing
information.

```python
>>> Run(text="hello").to_dict()
{'text': 'hello'}
>>> Run(text="hello", bold=True, font_size=14.0).to_dict()
{'text': 'hello', 'bold': True, 'font_size': 14.0}
```

### Markdown rendering

The Markdown converter handles four cases per run:

| State                | Output                    |
| -------------------- | ------------------------- |
| `bold and italic`    | `***text***`              |
| `bold` only          | `**text**`                |
| `italic` only        | `_text_`                  |
| `href` set           | `[text](url)` (composable with bold/italic) |
| no formatting        | `text` (unchanged)        |

Underline is **never** rendered in Markdown output (no GFM syntax for
it). The HTML fallback path used for complex tables does emit `<u>`.

A paragraph's runs are only rendered with this formatting if at
**least one** run has `bold`, `italic`, `underline`, or `href`.
Otherwise the converter falls back to the flat `paragraph.text`.
This avoids emitting the same characters twice when run boundaries
don't carry useful information.

### Special run content

Some paragraph content is not authored text but is inlined by the
parser as synthetic runs:

| Source                   | Inlined as                          |
| ------------------------ | ----------------------------------- |
| HWPX equation            | `[수식]` placeholder — equation content is not extractable |
| Footnote                 | `[footnote: text]` at the reference point |
| Endnote                  | `[endnote: text]` at the reference point |
| Text box (`gso`)         | raw text, inlined at the anchor position |

These appear as `Run` instances in `paragraph.runs` with no special
formatting flags. They are also reflected in `paragraph.text`.

Equation content is stored in Hancom's proprietary `<hp:script>` notation,
not MathML — the parser emits `[수식]` and does not attempt to parse the
formula.

---

## `Table`, `Row`, `Cell`

::: openhanji.models.document.Table

::: openhanji.models.document.Row

::: openhanji.models.document.Cell

### `Cell.blocks` is the canonical storage

`Cell.blocks` is a `list[Paragraph | Table | ImageRef]` preserving
**every** child block in document order, including nested tables and
images. The convenience properties — `cell.paragraphs`, `cell.tables`,
`cell.images` — are filtered views over `blocks`.

`cell.text` recursively flattens `blocks` to plain text:

- Paragraphs contribute their `text`.
- Tables become tab-joined rows separated by newlines.
- Images contribute `[Image: caption]` only when a caption is set.
- Empty pieces are dropped.

Use `cell.text` for RAG ingestion when you want the cell as a single
string; use `cell.blocks` (or its filtered views) for structure-aware
rendering that needs to see the nested tables.

### `Cell.to_dict()` output

```json
{
  "text": "flattened plain text of the cell",
  "col_span": 1,
  "row_span": 1,
  "blocks": [...]
}
```

`"text"` is the recursive plain-text flattening of `cell.blocks` (same
result as `cell.text`). `"blocks"` holds each child block serialised with
its own `to_dict()` — paragraphs, nested tables, and image refs all appear
here in document order.

### Spans

`col_span` and `row_span` default to `1`. Cells with span > 1 trigger
the **complex table** path in the Markdown converter — the entire
table falls back to HTML `<table>` instead of GFM pipes, because GFM
has no syntax for cell spans.

A table is "simple" (eligible for GFM rendering) only when **every**
cell satisfies all of:

- `col_span == 1` and `row_span == 1`
- exactly one block in `cell.blocks`
- that block is a `Paragraph` (no nested tables or inline images)
- the paragraph's `text` contains no newlines

Any cell failing any of these conditions forces the whole table to
HTML.

### Captions

`Table.caption` is `None` when the source has no caption. The
Markdown converter emits the caption as `*caption text*` italic
above the table for simple tables, and as `<caption>` inside the
HTML fallback for complex tables.

---

## `ImageRef`

::: openhanji.models.document.ImageRef

### Binary extraction

By default, `openhanji.open()` **skips all binary reads** from `BinData/`.
Every `ImageRef` in the document has `data=None` and `format=None` in
the default path — the structural position, caption, and dimensions are
preserved, but no zip decompression happens.

Pass `with_images=True` to read and attach the binaries:

```python
doc = openhanji.open("document.hwpx", with_images=True)
for img in doc.images:
    print(img.format, len(img.data))   # e.g. "png", 42318
```

When `with_images=True`:

- `data` holds the raw bytes.
- `format` is the lower-cased extension of the binary part filename
  (`"png"`, `"jpg"`, `"bmp"`, etc.).

When the `binaryItemIDRef` can't be resolved (missing binary part),
`ImageRef` still appears at the correct position with `data=None` and
`format=None` even in `with_images=True` mode.

### JSON serialisation

`data` is base64-encoded inline when present, or `null` in the default
(placeholder) path. The default JSON output is compact; passing
`with_images=True` and then serialising an image-heavy document can
produce very large output.

### Markdown rendering

When `data` and `format` are both present, the Markdown converter
emits a base64 data URI:

```markdown
![caption](data:image/png;base64,iVBORw0KGgoAAA…)
```

Otherwise (the default) it emits a placeholder:

```markdown
![caption](image_0)
```

The placeholder name is `image_{image_seq}`, unique across the
document. Downstream tooling can substitute real paths at these
anchors.

---

## `Metadata`

::: openhanji.models.document.Metadata

### Field provenance

Metadata is sourced from two places inside the HWPX zip, with
different reliability:

The OWPML model (`hancom-io/hwpx-owpml-model`) designates `content.hpf`
as the OPF package file — the standard place for metadata in OOXML-style
formats. `header.xml` holds the document's internal Dublin Core fields.
In practice, `header.xml` tends to be more reliably populated in
Hancom-saved files, so the parser reads it first and uses `content.hpf`
only to fill in fields that `header.xml` left empty.

- **`title`** — read from `header.xml` (Dublin Core `title` field)
  first; `content.hpf` (`<opf:title>`) fills in only if `header.xml`
  left it empty.
- **`author`** — read from `header.xml` (`creator` / `author` field)
  first; `content.hpf` (`<opf:meta name="creator">`) fills in only if
  empty. Often the OS username rather than a display name when the user
  never configured one.
- **`subject`** — read from `header.xml` first; `content.hpf`
  (`<opf:meta name="subject">`) fills in only if empty.
- **`created_at`, `modified_at`** — `<opf:meta name="CreatedDate/ModifiedDate">`
  in `content.hpf`. Reliably present in HWPX files.
- **`keywords`** — `<opf:meta name="keyword">` in `content.hpf`, split
  on commas and newlines. Both separators appear in HWPX files.
- **`page_count`** — populated from `content.hpf` when present; `None` otherwise.

---

## `ParagraphStyle`

::: openhanji.models.document.ParagraphStyle

A string enum. The `.value` is the canonical wire format used in JSON
output:

| Member            | `.value`           | Markdown            | Notes                          |
| ----------------- | ------------------ | ------------------- | ------------------------------ |
| `HEADING1`–`HEADING6` | `"HEADING1"` … | `#` … `######`      | `level` mirrors the depth.     |
| `BODY`            | `"BODY"`           | (paragraph as-is)   | The default.                   |
| `LIST_UNORDERED`  | `"LIST_UNORDERED"` | `- text`            | `level` controls indentation.  |
| `LIST_ORDERED`    | `"LIST_ORDERED"`   | `1. text`           | All ordered items emit `1.`.   |

The "all ordered items emit `1.`" behaviour is deliberate — Markdown
auto-numbers regardless of the literal digit, and using `1.` for
every line keeps source diffs stable when items are reordered.

### Heading detection

`ParagraphStyle` is resolved by four steps that run in order:

1. **Outline level / style name** — the `outlineLevel` XML attribute,
   or a `styleIDRef` name matching a heading pattern (`heading`, `head`,
   `title`). Reliable when the author applied Hancom's built-in heading
   styles. Suppressed when `heading_detection="none"`.

2. **List detection** — `list_kind` from the `para_shapes` index
   (`ordered` maps to `LIST_ORDERED`, `unordered` maps to `LIST_UNORDERED`), or a
   style name containing `"list"` / `"bullet"`. Runs regardless of
   `heading_detection` mode.

3. **Font heuristic** — only when `heading_detection="auto"` and steps
   1–2 produced no result. Inspects the dominant run font face and font
   size. Current thresholds (calibrated from Korean business documents):

   | Font face in `_HEADING_FONT_FACES` | Min font size | Bold required | Inferred style |
   | ---------------------------------- | ------------- | ------------- | -------------- |
   | Yes                                | ≥ 14 pt       | No            | `HEADING1`     |
   | Yes                                | ≥ 12 pt       | No            | `HEADING2`     |
   | No                                 | ≥ 18 pt       | **Yes**       | `HEADING1`     |
   | No                                 | ≥ 16 pt       | **Yes**       | `HEADING2`     |

   Fonts in `_BODY_FONT_FACES` (e.g. `맑은 고딕`) are never promoted —
   the heuristic returns `BODY` immediately regardless of size or bold.
   For all other fonts not in either set, bold is required as a
   co-signal to avoid promoting large body text to headings.
   Paragraphs longer than 120 characters are never inferred as
   headings, regardless of font. When neither path matches, the
   paragraph is `BODY`.
