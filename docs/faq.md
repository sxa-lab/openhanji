# FAQ

## 1. Who is this for?

`openhanji` is for Python code that needs to read `.hwpx` files without
Hancom Office or a PDF/DOCX conversion step.

Typical users:

- **RAG and NLP projects** that need text from legal filings, academic
  papers, business reports, or other Hancom Office documents. `to_text()`
  gives plain text for chunking; `openhanji.converters.json.to_json()`
  gives structured data for metadata-aware retrieval.
- **NLP researchers** working with documents in which a significant
  share of the source material is in HWPX format.
- **Data engineers** processing document collections from organisations
  that use Hancom Office. The CLI handles directory batches and reports
  per-file success, skip, and error counts.
- **Backend developers** adding HWPX export or preview support to a
  web application or document management system.
- **Open-source contributors** building HWPX tooling.

`openhanji` is pure Python, Apache 2.0.

---

## 2. Does it support `.hwp`?

Not yet. `.hwp` is Hancom's older binary format (pre-2010) and requires
a completely different parser. It is planned for v0.2. `.hwpx` is the
current OOXML-style ZIP + XML format and is supported from v0.1.0.

---

## 3. Why is `metadata.title` often `None`?

The parser reads title from `header.xml` (Dublin Core fields) first,
then falls back to `content.hpf` (the OWPML OPF package file, which
is the standard metadata location per the `hancom-io/hwpx-owpml-model`
spec). In practice, `header.xml` is more reliably populated in
Hancom-saved files, which is why it takes precedence in our parser.

Hancom Office leaves the title field empty in both files unless the
author explicitly fills in the document properties panel. The title
shown in the document window is the filename — it is not written into
the XML metadata unless explicitly set. This is observed behavior
across many HWPX files, not a formally documented guarantee.

`metadata.created_at`, `metadata.modified_at`, and `metadata.keywords`
come from `content.hpf` OPF metadata when present.

---

## 4. Why are images placeholders by default?

Reading image binaries from the HWPX zip means decompressing every
`BinData/` entry. For text extraction, that work is usually unnecessary
and can make Markdown/JSON output much larger.

The default (`with_images=False`) skips all binary reads. `ImageRef`
nodes are still present in the document tree at their correct positions,
with caption and dimensions preserved. `format` remains `None` because
the binary part is not read. Pass `with_images=True` to attach the actual
bytes and format:

```python
doc = openhanji.open("document.hwpx", with_images=True)
```

---

## 5. Why doesn't `doc.tables` include nested tables?

`doc.tables` is a filtered view over `doc.blocks`, which holds only
**top-level** blocks. Tables nested inside table cells are stored on
`cell.blocks` and are intentionally not surfaced at the top level —
flattening them there would lose their structural context and make the
position ambiguous.

To reach nested tables:

```python
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for nested in cell.tables:   # nested tables here
                ...
```

`cell.text` recursively flattens everything — including nested tables —
to plain text. Use it for RAG chunking where structure is not needed.

---

## 6. What is the difference between `to_markdown()` and `to_text()` for RAG?

Use `to_text()` when you want plain input for a text
splitter or embedding model. It strips all Markdown syntax, flattens
tables to tab-separated rows, and drops image data entirely. No `#`,
no `**`, no `|` — just text.

Use `to_markdown()` when structure matters — heading hierarchy, table
layout, bold emphasis. GFM renders well in most LLM context windows
and gives the model more to work with than a flat text dump.

Use `openhanji.converters.json.to_json()` when you need structured data:
run-level formatting, paragraph styles, image positions, and metadata for
structured retrieval, reranking, or custom rendering.

---

## 7. Why does a table appear before its heading in `doc.blocks`?

This reflects the order elements appear in the source XML, not a parser
bug. Hancom Office can write a section heading `<hp:p>` after the table
it introduces in the XML stream. The parser preserves source order.

If your code needs heading-before-content order, walk `doc.blocks` and
reorder heading/table pairs:

```python
reordered = []
i = 0
while i < len(doc.blocks):
    block = doc.blocks[i]
    if (
        isinstance(block, openhanji.Table)
        and i + 1 < len(doc.blocks)
        and isinstance(doc.blocks[i + 1], openhanji.Paragraph)
        and doc.blocks[i + 1].style.value.startswith("HEADING")
    ):
        reordered.append(doc.blocks[i + 1])
        reordered.append(block)
        i += 2
    else:
        reordered.append(block)
        i += 1
```

---

## 8. Can I use `openhanji` inside a LangChain or LlamaIndex pipeline?

Yes. The typical integration pattern is a document loader that calls
`openhanji.open()` and returns chunks from `to_text()` or structured
nodes from `openhanji.converters.json.to_json()`. Neither LangChain nor
LlamaIndex has a built-in HWPX loader.

A minimal LangChain-style loader:

```python
import openhanji

def load_hwpx(path: str) -> list[str]:
    doc = openhanji.open(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]
```

---

## 9. Is `openhanji` affiliated with Hancom Inc.?

No. `openhanji` is an independent open-source project developed by
**SxA Lab**. "HWP" and "HWPX" are file formats developed by Hancom Inc.
This project interoperates with those formats but is not endorsed by,
affiliated with, or supported by Hancom Inc.
