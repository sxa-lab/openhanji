# Changelog

## 0.1.0 - unreleased

Initial HWPX-focused release of OpenHanji.

This release includes:

- HWPX parsing into a structured `Document` model.
- Markdown, JSON, and plain-text converters.
- CLI commands: `openhanji extract` and `openhanji info`.
- Section-aware output with headers, footers, tables, image references, and
  nested table-cell content.
- Optional image binary loading through the Python API (`with_images=True`)
  and CLI (`--with-images`).
- Heading detection modes: `auto`, `structural`, and `none`.
- Strict mode for validation-oriented parsing.
- Batch CLI processing for recognized Hancom file extensions.

### Known Caveats

- `.hwp`, `.cell`, and `.show` are recognized but not implemented yet.
- Equation extraction emits placeholders instead of full formula semantics.
- `with_images=True` can produce large Markdown/JSON output for image-heavy
  documents.
