# Exceptions

All user-facing exceptions raised by `openhanji` inherit from
`OpenHanjiError`, so a single catch handles every parser-level
failure:

```python
import openhanji

try:
    doc = openhanji.open("document.hwpx", strict=True)
except openhanji.OpenHanjiError as e:
    log.error("openhanji failed: %s", e)
```

Note that `FileNotFoundError` (raised by `openhanji.open()` when the
path doesn't exist) is a **standard library** exception and is **not**
an `OpenHanjiError` subclass. Catch it separately if you need to
distinguish "file missing" from "file present but unparseable".

## Hierarchy

```
Exception
└── OpenHanjiError
    ├── NotSupportedError
    ├── CorruptedFileError
    └── UnknownRecordError
```

---

## `OpenHanjiError`

::: openhanji.exceptions.OpenHanjiError

The base class. Catch this to handle every parser-level failure with
one `except` clause. Direct instances are not raised by the library —
only the subclasses below are.

---

## `NotSupportedError`

::: openhanji.exceptions.NotSupportedError

Raised by [`openhanji.open()`](openhanji.md#open) when the file
cannot be opened. Extensions `.hwp`, `.cell`, and `.show` are
recognised but not yet implemented — they raise with
"not yet implemented. Coming soon!". Any other suffix raises with
"not a supported Hancom Office format" listing the supported
extensions.

The error message always includes the offending suffix.

```python
try:
    doc = openhanji.open("legacy.hwp")
except openhanji.NotSupportedError as e:
    print(e)   # → "'.hwp' is not yet implemented. Coming soon!"
```

---

## `CorruptedFileError`

::: openhanji.exceptions.CorruptedFileError

Raised by parsers when the file is structurally broken:

- The HWPX file is not a valid zip — raised in both modes.
- A section XML part is not well-formed — raised in strict mode only;
  in non-strict mode the malformed section is logged and skipped.
- Any other unexpected exception during parse is wrapped and
  re-raised as `CorruptedFileError` — raised in both modes.

Missing optional parts (`content.hpf`, `header.xml`) are logged as
warnings and do not raise.

---

## `UnknownRecordError`

::: openhanji.exceptions.UnknownRecordError

Raised by parsers in **strict mode only** when a block-level XML
element appears inside a section that the parser has no handler for
and isn't in the `_SKIP_TAGS` allowlist.

In default (non-strict) mode, the same element is silently skipped
and parsing continues. This is what makes the default mode robust
against HWPX files that contain undocumented or version-specific
block types.

```python
try:
    doc = openhanji.open("weird.hwpx", strict=True)
except openhanji.UnknownRecordError as e:
    log.error("strict-mode parse failed: %s", e)
    # fall back to lossy parse
    doc = openhanji.open("weird.hwpx", strict=False)
```
