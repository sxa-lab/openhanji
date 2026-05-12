[한국어](https://github.com/sxa-lab/openhanji/blob/main/README.md) | [English](https://github.com/sxa-lab/openhanji/blob/main/README.en.md) | [中文](https://github.com/sxa-lab/openhanji/blob/main/README.zh.md) | [License](https://github.com/sxa-lab/openhanji/blob/main/LICENSE) | [Notice](https://github.com/sxa-lab/openhanji/blob/main/NOTICE)

[![PyPI version](https://badge.fury.io/py/openhanji.svg)](https://badge.fury.io/py/openhanji)
[![Python Version](https://img.shields.io/pypi/pyversions/openhanji.svg)](https://pypi.org/project/openhanji/)
[![Tests](https://github.com/sxa-lab/openhanji/actions/workflows/ci.yml/badge.svg)](https://github.com/sxa-lab/openhanji/actions/workflows/ci.yml)
[![Downloads](https://static.pepy.tech/badge/openhanji)](https://pepy.tech/project/openhanji)
[![ReadTheDocs](https://img.shields.io/readthedocs/openhanji?label=ReadTheDocs)](https://openhanji.readthedocs.io/)

**Open-source Python parser and converter for Hancom Office documents**

`v0.1.0` parses HWPX documents into a structured Python document model that can be exported as:
- JSON
- Markdown
- plain text

**Useful for:**
- document ingestion and search
- RAG and NLP workflows
- backend services that need HWPX text or metadata

---

## Install

```bash
pip install openhanji
```

## Quickstart

```python
import openhanji

doc = openhanji.open("report.hwpx")

# Iterate paragraphs
for paragraph in doc.paragraphs:
    print(paragraph.text)

# Iterate all blocks (flattened across sections)
for block in doc.blocks:
    print(type(block).__name__, getattr(block, "text", ""))

# Structured output
print(doc.to_json())                        # flat "body" array (default)
print(doc.to_json(mode="structured"))       # section-aware array
print(doc.to_markdown())
print(doc.to_text())

# Metadata
print(doc.metadata.title)
print(doc.metadata.author)
```

## CLI

Markdown output (default):

```bash
openhanji extract document.hwpx
```

Recursive plain-text extraction:

```bash
openhanji extract document.hwpx --format text
```

JSON output with run-level formatting metadata.

Non-default `bold`, `italic`, `font_size`, and `color` values are included in the output.

```bash
openhanji extract document.hwpx --format json
```

Short format alias:

```bash
openhanji extract document.hwpx -f json
```

JSON includes resolved `font_face` on runs, plus paragraph `align` and `style_name` values when defined in `header.xml`.

Fields at default values are omitted — a plain run serialises as:

```json
{"text": "..."}
```

Save output to a file:

```bash
openhanji extract document.hwpx -o output.md
```

Recursively convert every `.hwpx` under the input directory into the output directory:

```bash
openhanji extract ./docs/ -o ./output/ -f markdown
```

Strict mode raises on unknown content and malformed present XML parts
instead of skipping them:

```bash
openhanji extract document.hwpx --strict
```

Read and embed image binaries as base64.

By default, binary image reads are skipped and images render as placeholders.

```bash
openhanji extract document.hwpx --with-images
```

Heading classification strategy (`auto`, `structural`, `none`).

`structural` uses only structural heading signals.
`none` treats all paragraphs as `BODY`.

```bash
openhanji extract document.hwpx --heading-detection structural
openhanji extract document.hwpx --heading-detection none
```

Print version:

```bash
openhanji --version
```

Print document metadata and content statistics, including title, author, keywords, dates, page count, and paragraph/table/image counts:

```bash
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
