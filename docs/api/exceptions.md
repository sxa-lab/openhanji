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
extension is not in the supported set. In v0.1.0 this includes:

- `.hwp` — binary Hancom format. Different parser entirely; planned
  for v0.2.
- `.cell`, `.show`, `.doc`, `.docx`, `.pdf`, anything else.

The error message includes the offending suffix so callers can log
which extension was rejected.

```python
try:
    doc = openhanji.open("legacy.hwp")
except openhanji.NotSupportedError as e:
    print(e)   # → "'.hwp' is not supported."
```

---

## `CorruptedFileError`

::: openhanji.exceptions.CorruptedFileError

Raised by parsers when the file structure itself is broken:

- The HWPX file is not a valid zip.
- Required XML parts (`content.hpf`, `header.xml`, at least one
  `section*.xml`) are missing.
- An XML part is not well-formed.

Raised in **both** strict and non-strict modes — corruption is never
recoverable by skipping content, since the corruption affects the
overall document structure rather than a specific element.

---

## `UnknownRecordError`

::: openhanji.exceptions.UnknownRecordError

Raised by parsers in **strict mode only** when an XML element appears
that the parser doesn't have a handler for and isn't in the
`_SKIP_TAGS` skip list.

In default (non-strict) mode, the same condition produces a `WARNING`
log entry instead and the element is skipped. This is what makes the
default mode robust against HWPX files, which routinely
contain undocumented or version-specific elements.

The exception message identifies the unrecognised element and its
parent context, so strict-mode callers can diagnose what triggered
the failure:

```python
try:
    doc = openhanji.open("weird.hwpx", strict=True)
except openhanji.UnknownRecordError as e:
    log.error("strict-mode parse failed: %s", e)
    # fall back to lossy parse
    doc = openhanji.open("weird.hwpx", strict=False)
```

The "fall back to non-strict" pattern is common in pipelines that
want to know about unknown content but don't want it to fail the
batch.
