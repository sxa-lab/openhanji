# Quickstart

## Install

```bash
pip install openhanji          # pip
uv pip install openhanji       # uv (venv mode)
uv add openhanji               # uv (project mode)
poetry add openhanji           # poetry
```

For development (tests, linting, type-checking):

```bash
pip install -e ".[dev]"
```

## Open a document

```python
import openhanji

doc = openhanji.open("document.hwpx")
```

Returns a [`Document`](api/document.md#document). Raises
[`NotSupportedError`](api/exceptions.md#notsupportederror) for
unsupported extensions, including `.hwp`.

### Options

```python
doc = openhanji.open("document.hwpx", strict=True)
# raises on unknown XML or malformed present XML parts instead of skipping

doc = openhanji.open("document.hwpx", heading_detection="structural")
# "auto" (default) | "structural" | "none"

doc = openhanji.open("document.hwpx", with_images=True)
# read image binaries; default skips all BinData/ reads
```

See [`openhanji.open()`](api/openhanji.md) for the full parameter reference.

## Walk the document

```python
# all top-level blocks in document order
for block in doc.blocks:
    ...

# filtered views (do not recurse into tables)
for para in doc.paragraphs:
    print(para.style.value, para.text)

for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text)           # flattened plain text
            for block in cell.blocks:  # structure-aware walk
                ...

for image in doc.images:
    print(image.caption, image.width, image.height)
```

### Lists

```python
from openhanji.models.document import ParagraphStyle

for para in doc.paragraphs:
    if para.style == ParagraphStyle.LIST_ORDERED:
        print(f"{para.level * '  '}1. {para.text}")
    elif para.style == ParagraphStyle.LIST_UNORDERED:
        print(f"{para.level * '  '}- {para.text}")
```

Lists inside table cells work identically — `cell.blocks` contains
`Paragraph` instances with list styles.

### Sections, headers, and footers

```python
for section in doc.sections:
    print(section.index, section.source_path)

# flattened across all sections
for block in doc.headers:
    ...
for block in doc.footers:
    ...
```

### Run-level formatting and hyperlinks

```python
for para in doc.paragraphs:
    for run in para.runs:
        if run.bold or run.italic:
            print(run.text, run.font_size, run.color)
        if run.href:
            print(f"{run.text!r} → {run.href}")
```

See [`Run`](api/document.md#run) for the full field reference.

## Special content

**Equations** are inlined as `[수식]` at their position in the paragraph
flow. HWPX stores formula content in Hancom's proprietary notation;
the formula itself is not extracted.

**Footnotes and endnotes** are inlined as `[footnote: text]` /
`[endnote: text]` at the point of the reference.

**Text boxes** are inlined at the position where they are anchored in
the flow.

## Images

```python
# default — structure only, no binary reads
for img in doc.images:
    print(img.caption, img.width, img.height)  # always available
    print(img.data)    # None

# opt in to binaries
doc = openhanji.open("document.hwpx", with_images=True)
for img in doc.images:
    print(img.format, len(img.data))  # "png", 42318
```

Images inside cells are in `cell.images`.

## Convert to JSON / Markdown / text

```python
from openhanji.converters.json import to_json

print(to_json(doc))                     # flat body list, run-level detail
print(to_json(doc, mode="structured"))  # one object per section
print(doc.to_markdown())                # GFM; complex tables → HTML
print(doc.to_text())                    # plain text, no formatting
```

| Format     | Best for                                 | Note                                             |
| ---------- | ---------------------------------------- | ------------------------------------------------ |
| `json`     | Structured metadata and document blocks  | Images `null` by default; use `with_images=True` |
| `markdown` | LLM context, human-readable rendering    | Underline HTML-only; complex tables fall back to `<table>`  |
| `text`     | Plain-text chunking, search indexing     | Drops all formatting                             |

See [`Document`](api/document.md#document) for the JSON schema and
Markdown rendering rules.

## Read metadata

```python
m = doc.metadata
print(m.title, m.author, m.subject)
print(m.created_at, m.modified_at)
print(m.keywords)   # list[str]
print(m.page_count) # int or None
```

Title, author, and subject are read from `header.xml` (Dublin Core
fields) first; `content.hpf` (the OWPML OPF package file) fills in
only what `header.xml` left empty. In practice `header.xml` is more
reliably populated in Hancom-saved files. Dates and keywords come from
`content.hpf` only and are reliably present in HWPX files.

## What's next

- [CLI](cli.md) — extract from the command line, including batch directory mode.
- [API reference](api/index.md) — complete reference for every type and function.
- [Format support](formats.md) — coverage matrix and known limitations.
