# openhanji

**Open-source Python parser for Hancom Office HWPX documents.**

`openhanji` reads `.hwpx` files into a typed `Document` object and emits
JSON, Markdown, or plain text. It is useful when Python systems need to
consume HWPX files without depending on Hancom's proprietary stack.

## Highlights

- **Direct HWPX parsing.** Parses the OWPML XML inside the HWPX zip; no
  PDF or DOCX conversion step.
- **Typed document model.** `Document`, `Paragraph`, `Run`, `Table`, `Cell`,
  `ImageRef`, `Metadata` — plain dataclasses, fully type-checked under
  `mypy --strict`.
- **Three output formats.** `openhanji.converters.json.to_json()`
  (structured data), `to_markdown()` (GFM + HTML fallback for complex
  tables), `to_text()` (recursive plain-text extraction).
- **Strict mode available.** Unknown XML is skipped and logged at
  `WARNING`; pass `strict=True` to escalate it to an exception.
- **Hancom metadata support.** Hangul font faces are resolved from
  `header.xml` and preserved in the run-level output. Heading detection
  handles both structural (`outlineLevel`) and display-font heuristics.
- **Opt-in image binaries.** The parser records image positions without
  reading binary payloads. Pass `with_images=True` when the bytes are
  needed.

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
