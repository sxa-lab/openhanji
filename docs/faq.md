# FAQ

## 1. Who is this for?

`openhanji` is for any Python developer or team that needs to read
`.hwpx` files — no Hancom Office installed, no conversion to PDF or
DOCX required.

Typical users:

- **AI / LLM engineers** building RAG pipelines that need to ingest
  legal filings, academic papers, business reports, or any document
  authored in Hancom Office. `to_text()` gives you clean plain text
  for chunking; `to_json()` gives you the full structured tree for
  metadata-aware retrieval.
- **NLP researchers** working with documents in which a significant
  share of the source material is in HWPX format.
- **Data engineers** building document ingestion pipelines for
  organisations that use Hancom Office as their primary office suite —
  common in public sector, education, legal, and enterprise environments.
- **Backend developers** adding HWPX export or preview support to a
  web application or document management system.
- **AI agents and autonomous pipelines** that need to read, extract, or
  reason over HWPX documents as part of a tool call or workflow step.
  `openhanji` has no interactive dependencies — no GUI, no Office
  installation, no subprocess calls to external tools.
- **Open-source contributors** who want a well-typed, well-tested
  foundation to build higher-level HWPX tooling on top of.

`openhanji` is pure Python, Apache 2.0.

---

## 2. Does it support `.hwp`?

Not yet. `.hwp` is Hancom's older binary format (pre-2010) and requires
a completely different parser. It is planned for v0.2. `.hwpx` is the
current OOXML-style ZIP + XML format and is fully supported from v0.1.0.

---

## 3. Why is `metadata.title` always `None`?

The `<dc:title>` field in `header.xml` is rarely populated by Hancom
Office when saving a document. The title you see in the document window
is typically just the filename — it is not written into the XML metadata
unless the author explicitly filled in the document properties panel.

`metadata.created_at`, `metadata.modified_at`, and `metadata.keywords`
come from `content.hpf` OPF metadata and are reliably present. Use
those for document identification in pipelines.

---

## 4. Why are images placeholders by default?

Reading image binaries from the HWPX zip means decompressing every
`BinData/` entry — potentially dozens of zip reads per document. For
batch ingestion pipelines that don't need the actual pixels (most RAG
and NLP use cases), this is wasted work that balloons output size by
5–10×.

The default (`with_images=False`) skips all binary reads. `ImageRef`
nodes are still present in the document tree at their correct positions,
with caption, dimensions, and format preserved. Pass `with_images=True`
to attach the actual bytes:

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
to plain text, which is usually what RAG pipelines want.

---

## 6. What is the difference between `to_markdown()` and `to_text()` for RAG?

Use `to_text()` when you want the cleanest possible input for a text
splitter or embedding model. It strips all Markdown syntax, flattens
tables to tab-separated rows, and drops image data entirely. No `#`,
no `**`, no `|` — just text.

Use `to_markdown()` when structure matters — heading hierarchy, table
layout, bold emphasis. GFM renders well in most LLM context windows
and gives the model more to work with than a flat text dump.

Use `to_json()` when you need the full fidelity tree — run-level
formatting, paragraph styles, image positions, metadata — for
structured retrieval, reranking, or custom rendering.

---

## 7. Why does a table sometimes appear before its heading in `doc.blocks`?

This reflects the order elements appear in the source XML, not a parser
bug. HWPX documents are sometimes authored with a section heading
`<hp:p>` placed after the table it introduces in the XML stream. The
parser faithfully preserves source order.

If your pipeline needs heading-before-content order, walk `doc.blocks` and
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
nodes from `to_json()`. Neither LangChain nor LlamaIndex has a built-in
HWPX loader.

A minimal LangChain-style loader:

```python
import openhanji

def load_hwpx(path: str) -> list[str]:
    doc = openhanji.open(path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]
```

---

## 9. Is `openhanji` affiliated with Hancom Inc.?

No. `openhanji` is an independent open-source project developed by **SxA Lab**. "HWP" and
"HWPX" are file formats developed by Hancom Inc. This project
interoperates with those formats but is not endorsed by, affiliated
with, or supported by Hancom Inc.
