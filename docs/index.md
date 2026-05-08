# openhanji

**Open-source Python parser for Hancom Office HWPX documents.**

`openhanji` reads `.hwpx` files into a typed `Document` object and emits
JSON, Markdown, or plain text. Built for AI / NLP / RAG pipelines that
need to consume HWPX files without depending on Hancom's proprietary
stack.

## Highlights

- **HWPX-native.** Parses the OWPML XML inside the HWPX zip directly; no
  conversion to PDF or DOCX in the pipeline.
- **Typed document model.** `Document`, `Paragraph`, `Run`, `Table`, `Cell`,
  `ImageRef`, `Metadata` — plain dataclasses, fully type-checked under
  `mypy --strict`.
- **Three output formats.** `to_json()` (full fidelity), `to_markdown()`
  (GFM + HTML fallback for complex tables), `to_text()` (recursive
  plain-text extraction).
- **Never crashes on unknown content.** Unknown XML is skipped and
  logged at `WARNING`. Pass `strict=True` to escalate to exceptions.
- **Format-native.** Hangul font faces are resolved from `header.xml` and
  preserved in the run-level output. Heading detection handles both
  structural (`outlineLevel`) and display-font heuristics.
- **Fast by default.** Image binaries are skipped unless
  `with_images=True`, so the common extraction path only reads XML and
  metadata parts.

## Install

```bash
pip install openhanji            # pip
uv pip install openhanji         # uv
poetry add openhanji             # poetry
```

## 30-second tour

```python
import openhanji

doc = openhanji.open("document.hwpx")

for paragraph in doc.paragraphs:
    print(paragraph.text)

print(doc.to_markdown())
```

Continue with the [Quickstart](usage.md), or jump straight to the
[API reference](api/index.md).

## Format support

| Format  | Status    | Notes                   |
| ------- | --------- | ----------------------- |
| `.hwpx` | Supported | v0.1.0, ZIP + OWPML XML |

See [Format support](formats.md) for the full coverage matrix.

## License

Apache 2.0 © [SxA Lab](https://github.com/sxa-lab).

See [NOTICE](https://github.com/sxa-lab/openhanji/blob/main/NOTICE) for
trademark attributions. "HWP" and "HWPX" are formats specified by
Hancom Inc. — this project is independent and unaffiliated.
