# Converters

Converters are **stateless functions** that walk `Document.blocks` and
emit a string in the target format. They live in
`openhanji.converters` and are invoked by the convenience methods on
`Document`:

```python
doc.to_markdown()   # → openhanji.converters.markdown.to_markdown(doc)
doc.to_text()       # → openhanji.converters.text.to_text(doc)
```

JSON output is implemented directly on the model
([`Document.to_json()`](document.md#to_json)) because every node has a
`to_dict()` method — there's no separate JSON converter.

---

## `to_markdown()`

::: openhanji.converters.markdown.to_markdown

Renders the document as GitHub Flavoured Markdown. Top-level blocks
are joined by **two newlines** (a blank line between them). Empty
paragraphs are dropped from the output.

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
one** run has `bold`, `italic`, or `underline`. Otherwise the
converter falls back to the flat `paragraph.text`, avoiding double
emission of the same characters when runs carry no useful formatting.

When the run path is taken, formatting maps as:

| Run state          | Output       |
| ------------------ | ------------ |
| bold + italic      | `***text***` |
| bold only          | `**text**`   |
| italic only        | `_text_`     |
| underline only     | `text`       |

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
preserves `colspan` / `rowspan`, nested tables (recursively), inline
images, and full run-level formatting (including `<u>` for underline).

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

Images without binary data fall back to a placeholder reference:

```markdown
![caption](image_0)
```

The placeholder is a hint for downstream tooling that wants to
substitute external image paths (e.g. extract images to `./images/`
and rewrite the references).

---

## `to_text()`

::: openhanji.converters.text.to_text

Plain-text rendering. One line per paragraph. Tables become
tab-separated rows joined by newlines. Images contribute
`[Image: caption]` only when a caption is set; uncaptioned images are
dropped.

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
