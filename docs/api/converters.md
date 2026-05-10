# Converters

Converters are **stateless functions** that walk `Document.blocks` and
emit a string in the target format. They live in
`openhanji.converters` and are called via convenience methods on
`Document`:

```python
doc.to_markdown()                # → openhanji.converters.markdown.to_markdown(doc)
doc.to_text()                    # → openhanji.converters.text.to_text(doc)
doc.to_json()                    # → openhanji.converters.json.to_json(doc)
doc.to_json(mode="structured")   # section-grouped mode
```

---

## `to_markdown()`

::: openhanji.converters.markdown.to_markdown

Renders the document as GitHub Flavoured Markdown. Top-level blocks
are joined by **two newlines** (a blank line between them). Empty
paragraphs are dropped from the output.

Headers and footers are emitted as HTML comments at the top and bottom
of the output respectively. When the header/footer region contains
multiple paragraphs, their texts are joined with ` | `:

```markdown
<!-- header: Header text -->

…body…

<!-- footer: Footer text -->
```

### Paragraph rendering rules

| Style                     | Output                                          |
| ------------------------- | ----------------------------------------------- |
| `HEADING1`–`HEADING6`     | `# text` … `###### text`                        |
| `LIST_UNORDERED` (level N)| `<2N spaces>- text`                             |
| `LIST_ORDERED` (level N)  | `<2N spaces>1. text` (always `1.`, see below)   |
| `BODY`                    | bare text                                       |

**Why `1.` for every ordered item?** Markdown auto-renumbers ordered
lists regardless of the literal digit. Always emitting `1.` keeps
source diffs stable when items are inserted, removed, or reordered —
no cascade of digit changes for a one-line edit.

### Run-level formatting

A paragraph's runs are walked with `_run_to_md` only if **at least
one** run has `bold`, `italic`, `underline`, or `href`. Otherwise the
converter falls back to the flat `paragraph.text`, avoiding double
emission of the same characters when runs carry no useful formatting.

When the run path is taken, formatting maps as:

| Run state          | Output                  |
| ------------------ | ----------------------- |
| bold + italic      | `***text***`            |
| bold only          | `**text**`              |
| italic only        | `_text_`                |
| underline only     | `text` (dropped)        |
| href set           | `[text](href)`          |

Underline has no GFM syntax, so it's silently dropped from Markdown
output. It survives in JSON and in the HTML fallback path used for
complex tables.

### Table rendering

Tables dispatch on `_is_simple_table()`:

```python
def _is_simple_table(table):
    # every cell must:
    #   - have col_span == 1 and row_span == 1
    #   - have exactly one block
    #   - that block must be a Paragraph
    #   - that paragraph's text must contain no newlines
```

If **all** cells pass: emit a GFM pipe table.

```markdown
| header1 | header2 |
| --- | --- |
| cell  | cell  |
```

The first row is treated as the header; if the source had no header
row, the first data row is rendered as the header anyway (GFM
requires one). Cell text has `\n` collapsed to spaces and `|` escaped
to `\|`. Short rows are padded with empty cells to the header width.

If **any** cell fails: fall back to HTML `<table>`. The HTML path
preserves `colspan` / `rowspan`, uses `<th>` for the first row and
`<td>` for the rest, nested tables (recursively), inline images, and
full run-level formatting (including `<u>` for underline).

This split is deliberate. GFM is preferable when it works — it's
human-readable and round-trippable through most Markdown tooling. But
GFM can't represent cell spans, multi-paragraph cells, or nested
tables, and silently truncating to the GFM-expressible subset would
lose information. The HTML fallback keeps the conversion lossless at
the cost of readability.

### Image rendering

Images with both `data` and `format` set are emitted as base64 data
URIs:

```markdown
![caption](data:image/png;base64,iVBORw0KGgo…)
```

Images without binary data fall back to a placeholder reference. The
alt text is the caption when set, or `image_{image_seq}` when not:

```markdown
![My caption](image_0)
![image_0](image_0)
```

The placeholder URL is always `image_{image_seq}`, unique across the
document. Downstream tooling can substitute real paths at these
anchors.

---

## `to_text()`

::: openhanji.converters.text.to_text

Plain-text rendering. One line per paragraph. Tables become
tab-separated rows joined by newlines. Images contribute
`[Image: caption]` only when a caption is set; uncaptioned images are
dropped.

Headers and footers are included as bracketed lines at the top and
bottom of the output. Multiple paragraphs in a header/footer region
are joined with ` | `:

```
[header: Header text]
…body…
[footer: Footer text]
```

Use this format for:

- RAG chunking where you want raw text without Markdown noise.
- Search index ingestion.
- Quick `grep`-able dumps of document content.

### What's lost

- All character formatting (bold, italic, underline, color, font).
- Paragraph alignment and named style.
- Heading hierarchy is flattened (no `#` markers, no indentation).
- List markers are dropped — list items render as plain text.
- Image binaries are entirely absent.

If you need any of those, use `to_markdown()` or `to_json()` instead.

### Recursive cell flattening

Table cells use [`Cell.text`](document.md#table-row-cell)
which recursively flattens nested tables. So a cell containing a
nested 2×2 table renders as four tab-separated values across two
lines within the cell, joined back into the outer cell's text.

---

## `to_json()`

::: openhanji.converters.json.to_json

### Parameters

| Parameter | Default    | Description |
|-----------|------------|-------------|
| `doc`     | —          | A `Document` instance. |
| `indent`  | `2`        | JSON indent width. |
| `mode`    | `"flat"`   | `"flat"` or `"structured"` (see below). |

### Flat mode (default)

```json
{
  "metadata": { … },
  "body": [ … ]
}
```

`body` is an ordered list of every top-level block (`paragraph`,
`table`, `image`). `headers` and `footers` are only present when the
document contains them.

### Structured mode

```json
{
  "metadata": { … },
  "sections": [
    {
      "index": 0,
      "source_path": "Contents/section0.xml",
      "blocks": [ … ],
      "headers": [ … ],
      "footers": [ … ]
    }
  ]
}
```

One object per [`Section`](document.md#section) — one section per
source XML file in the HWPX zip. `"headers"` and `"footers"` are
omitted when empty. The sum of all `section.blocks` lengths equals
the flat `body` length.
