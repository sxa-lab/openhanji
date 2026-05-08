[한국어](README.md) | [English](README.en.md) | [中文](README.zh.md) | [License](LICENSE) | [Notice](NOTICE)

**Open-source Python parser for Hancom Office HWPX documents**

`v0.1.0` is a Python package for parsing HWPX documents. It reads a document into a `Document` object and renders JSON, Markdown, or plain text output.

Top-level `doc.paragraphs`, `doc.tables`, and `doc.images` expose only
top-level body items. `doc.blocks` is the flat ordered list of all blocks
across all sections. Nested tables and images remain attached to their owning
cells through `cell.blocks`, while `cell.text` provides a recursive plain-text
summary of the full cell content.

---

## Install

```bash
pip install openhanji
```

## Quickstart

```python
import openhanji

doc = openhanji.open("report.hwpx")

#iterate paragraphs
for paragraph in doc.paragraphs:
    print(paragraph.text)

#iterate all blocks (flattened across sections)
for block in doc.blocks:
    print(type(block).__name__, getattr(block, "text", ""))

#structured output
print(doc.to_json())                        #flat "body" array (default)
print(doc.to_json(mode="structured"))       #section-aware array
print(doc.to_markdown())
print(doc.to_text())

#metadata
print(doc.metadata.title)
print(doc.metadata.author)
```

## CLI

```bash
#markdown (default) - headings and simple tables use Markdown; complex tables fall back to HTML
openhanji extract document.hwpx
```

```bash
#text - recursive plain-text extraction, including nested table content
openhanji extract document.hwpx --format text
```

```bash
#json - full fidelity; run-level bold/italic/font_size/color included when non-default
openhanji extract document.hwpx --format json
```

```bash
#short format alias
openhanji extract document.hwpx -f json
```

Run JSON includes resolved `font_face`, `align`, and `style_name` when
the values are set in `header.xml`. Fields at their default values are
omitted — a plain run serialises as `{"text": "..."}` only.

```bash
#save to file
openhanji extract document.hwpx -o output.md
```

```bash
#directory mode - recursively converts every .hwpx under the input directory into the output directory
openhanji extract ./docs/ -o ./output/ -f markdown
```

```bash
#strict mode - raise on unknown content instead of skipping it
openhanji extract document.hwpx --strict
```

```bash
#with-images - read and embed image binaries (base64-inlined)
#default skips binary reads; images render as placeholders
openhanji extract document.hwpx --with-images
```

```bash
#heading-detection - heading classification strategy (default: auto)
openhanji extract document.hwpx --heading-detection structural  #structural signals only
openhanji extract document.hwpx --heading-detection none        #all paragraphs are BODY
```

```bash
#print version
openhanji --version
```

```bash
#metadata - prints title, author, subject, keywords, dates, page count, and paragraph/table/image counts
openhanji info document.hwpx
```

---

## Format support

| Format | Status | Notes |
|--------|--------|-------|
| `.hwpx` | Supported | v0.1.0, ZIP + OWPML XML |

---

## Contributing

You are welcome to contribute to the project. Open an issue or PR.

---

## License

Apache 2.0 © [SxA Lab](https://github.com/sxa-lab)
