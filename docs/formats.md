# Format support

## File formats

| Format  | Status      | Notes                                                       |
| ------- | ----------- | ----------------------------------------------------------- |
| `.hwpx` | Supported | v0.1.0. ZIP container with OWPML XML parts. |

`openhanji.open()` dispatches by extension and raises
[`NotSupportedError`](api/exceptions.md#notsupportederror) for every
unsupported format, including `.hwp`.

## HWPX coverage

What the v0.1.0 HWPX parser extracts and preserves:

### Structure

- Section ordering across `section0.xml`, `section1.xml`, …
  (numeric, not lexicographic).
- Paragraphs, with style resolved from `header.xml`'s style table.
- Heading levels 1–6 mapped to `ParagraphStyle.HEADING1`…`HEADING6`.
  Two detection paths run in order: (1) structural — `outlineLevel`
  attribute or a style name matching a heading pattern in the styles
  table; (2) font heuristic — when the structural path yields no
  result, the parser falls back to font face and size. See
  [`ParagraphStyle` — Heading detection](api/document.md#heading-detection)
  for the thresholds.
- Ordered and unordered lists (`ParagraphStyle.LIST_ORDERED` /
  `LIST_UNORDERED`) with `level`.
- Paragraph alignment (`align`) and named style (`style_name`) when
  resolvable from `paraPr` / the styles table.
- Page headers and footers, extracted from `ctrl > header` / `ctrl > footer`
  elements and exposed as `doc.headers` / `doc.footers`
  (`list[Paragraph | Table | ImageRef]`). Blank header/footer regions
  produce empty lists.

### Run-level formatting

- Bold, italic, underline.
- Font size (points, float).
- Color (hex string, `None` when default/black).
- Hangul font face — resolved from `header.xml`'s `refList` font face
  table via the run's `charPrIDRef`.
- Hyperlink URL (`href`) — extracted from `HYPERLINK` field spans
  (`fieldBegin[type=HYPERLINK] > parameters > stringParam[name=Path]`).
  Runs inside the field span carry the URL; surrounding runs have
  `href=None`. Renders as `[text](url)` in Markdown and `<a href>` in
  HTML table output.

### Tables

- Rows and cells with `col_span` / `row_span`.
- Cell content as ordered `Cell.blocks` (preserves nested tables and
  images in their original position).
- `cell.text` recursively flattens the cell to plain text.
- Table captions when present.

### Images

- Image binary extracted from the HWPX zip via `binaryItemIDRef`.
- Format detected from the binary part's filename (`png`, `jpg`,
  `bmp`, etc.).
- Width, height, caption.
- Images without a resolvable `binaryItemIDRef` are kept as
  `ImageRef` nodes with `data=None` — the structural position is
  preserved even when the binary is missing.

### Metadata

- Title, author, and subject read from `header.xml` (Dublin Core
  fields) first. `content.hpf` (the OWPML OPF package file — the
  standard metadata location in OOXML-style formats) fills in only
  what `header.xml` left empty. In practice `header.xml` is more
  reliably populated in Hancom-saved files, which is why it is read
  first. Both sources are often empty for title and author.
- Created / modified dates, keywords, and page count from `content.hpf`
  OPF metadata only — these fields have no equivalent in `header.xml`.

## Inline content handling

Certain inline content types are extracted as labelled text rather than
separate structural nodes:

- **Footnotes and endnotes** — extracted at the point of reference,
  wrapped as `[footnote: text]` / `[endnote: text]`. No separate
  footnote list in the output.
- **Equations** — emit `[수식]` at the equation's position. HWPX stores
  formula content in Hancom's proprietary `<hp:script>` notation; it is
  not extracted.
- **Text boxes and drawing text** — extracted inline at the position
  the object appears in the paragraph flow.

## Body ordering

`Document.blocks` preserves the order items appear in the source XML.
In HWPX files, a section heading `<hp:p>` can appear in the XML
**after** the table it visually precedes — this is a quirk of how Hancom
Office writes section XML. The parser reflects source order exactly.
To get heading-before-content order, walk `blocks` and look ahead for
heading/table pairs.

## Known limitations (v0.1.0)

- **Revision tracking is not applied.** `trackChange` markers are
  skipped — the document body reflects the current accepted state of
  the text, not the revision history.
- **No pure geometry.** Non-text drawing elements (shapes, lines,
  arrows) carry no extractable text and are skipped without warning.
- **Non-hyperlink field markers are silent.** `FORMULA` and `MEMO`
  field types carry no extractable text and are ignored. `HYPERLINK`
  fields are extracted — see [Run-level formatting](#run-level-formatting).
- **Equations are placeholders only.** HWPX stores equation content in
  Hancom's proprietary `<hp:script>` notation — a format that is not
  documented publicly and is not MathML or LaTeX. There is no spec to
  parse it against, so extracting it would mean either shipping a
  reverse-engineered formula parser or outputting raw opaque bytes —
  neither is useful for a text/RAG pipeline. The parser emits `[수식]`
  at the equation's position to preserve the structural anchor.

Unknown XML elements outside these cases are skipped and logged at
`WARNING`. Use `strict=True` to escalate them to
[`UnknownRecordError`](api/exceptions.md#unknownrecorderror).

## Output format coverage

### JSON

Full-fidelity serialisation of the document tree. Every parsed field
is present: run-level `bold`, `italic`, `underline`, `font_size`,
`color`, `font_face`; paragraph `align` and `style_name`; table
`col_span` / `row_span`; image binary as base64. Fields at their
default values are omitted to keep output compact — a plain run
serialises as `{"text": "..."}` only.

Image binaries are base64-encoded inline when `with_images=True` is
passed to `openhanji.open()`. The default (`with_images=False`) skips
all binary reads from the zip — `ImageRef` nodes are still present at
their correct positions but emit `"data": null`.

Headers and footers are included as top-level `"headers"` and `"footers"`
arrays when non-empty. Each entry is a serialised block — paragraph,
table, or image — following the same schema as body blocks. The keys
are omitted entirely when the document has no header/footer content.

### Markdown

Targets GitHub Flavoured Markdown. Heading levels render as `#`–`######`.
Lists render with `-` / `1.` and indentation for nesting. Bold and
italic runs render as `**text**`, `_text_`, or `***text***` for combined.
Underline has no GFM equivalent — it is silently dropped from Markdown
output (preserved in JSON; rendered as `<u>` in the HTML table fallback).

Tables with no cell spans, single-paragraph cells, and no embedded
newlines render as GFM pipe tables. Any table with `colspan` / `rowspan`,
multi-paragraph cells, nested tables, or inline images falls back to an
HTML `<table>` block — which most Markdown renderers pass through.

Images render as base64 data URIs when `with_images=True`. The default
renders `![caption](image_N)` reference placeholders — no binary data
is read from the zip.

Headers and footers render as HTML comments at the top and bottom of the
output: `<!-- header: text -->` / `<!-- footer: text -->`. Multiple header
or footer paragraphs are joined with ` | `. The comments are omitted when
no header/footer content is present.

### Text

Plain-text extraction. One line per paragraph; formatting is stripped.
Tables are flattened to tab-separated rows. Nested tables are included
recursively via `cell.text`. Images contribute `[Image: caption]` when
a caption is present; uncaptioned images are omitted entirely.

Headers and footers render as labelled lines: `[header: text]` at the
start and `[footer: text]` at the end. Omitted when not present.

Use this format for search indexing and RAG chunking where Markdown
syntax would appear as noise.
