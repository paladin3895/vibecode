---
name: read-documents
description: 'Use when the user asks to read, extract, summarize, or inspect the contents of a .docx, .xlsx, or .pdf file. Extracts text and tables into Markdown so the content can be read directly into the agent''s context, using python-docx, pandas/openpyxl, and pdfplumber. Trigger phrases: "read this docx/xlsx/pdf", "extract text from this document/spreadsheet/pdf", "summarize this report/sheet", "what does this document say", "pull the data out of this file".'
---

# Read Documents (docx / xlsx / pdf)

## Purpose

Extract the readable content of Word documents, Excel spreadsheets, and
text-based PDFs as Markdown, so it can be read directly into the agent's
context. This skill is for **reading**, not for creating or round-tripping
back to the original file format.

## When to Use

- User shares a `.docx`, `.xlsx`/`.xls`, or `.pdf` file and asks to read,
  summarize, extract data from, or answer questions about it.
- Need tabular data from a spreadsheet or a PDF table as Markdown for
  further reasoning.

## Prerequisites

1. Make sure a Python environment is configured first (use
   `configure_python_environment`), then install packages with
   `install_python_packages` into that same environment — don't shell out to
   a different `python`/`pip` than the one configured.
2. Install only the libraries needed for the file type(s) at hand:
   - docx → `python-docx`
   - xlsx/xls → `pandas`, `openpyxl` (and `tabulate`, for `DataFrame.to_markdown`)
   - pdf → `pdfplumber`
3. [scripts/extract_text.py](./scripts/extract_text.py) detects a missing
   library itself and exits with the exact `pip install <package>` command
   to run — including a Windows note (`py -m pip install ...`) when `pip`
   isn't on `PATH`. Run it once; if it errors on a missing dependency,
   install that one package and re-run rather than pre-installing all of
   them speculatively.

## Procedure

1. Identify the file's extension to know what to expect: `.docx`,
   `.xlsx`/`.xls`, or `.pdf`.
2. Run [scripts/extract_text.py](./scripts/extract_text.py) against the file:
   ```
   python scripts/extract_text.py path/to/file.docx
   ```
   It prints Markdown to stdout: headings/paragraphs + tables for docx, one
   table per sheet for xlsx, and per-page text + detected tables for pdf.
3. For large files, redirect to a temp file instead of dumping everything
   into the conversation at once:
   ```
   python scripts/extract_text.py path/to/file.xlsx > /tmp/sheet.md
   ```
4. If a PDF page extracts empty/near-empty text, it's likely a scanned
   image. Tell the user OCR isn't supported by this skill rather than
   guessing at the content.
5. Read the actual extracted Markdown before summarizing or answering —
   don't paraphrase from the filename or assumptions.

## Format Notes

- **docx** (`python-docx`): paragraphs become Markdown lines; paragraphs
  styled `Heading N` become `#`×N headings; tables become Markdown tables.
- **xlsx** (`pandas` + `openpyxl`): each sheet renders as its own Markdown
  table under a `## <SheetName>` heading. Sheets over `--max-rows` (default
  200) are truncated with a note — ask the user before raising the limit to
  dump a huge sheet in full.
- **pdf** (`pdfplumber`): text per page under `## Page N`; tables detected
  via `page.extract_tables()` render as Markdown tables beneath the page
  text. No OCR — image-only PDFs will come back empty.

## Quality Checklist

- [ ] Correct library used per extension (python-docx / pandas+openpyxl / pdfplumber).
- [ ] Output is Markdown text, not raw Python objects/dicts dumped to the user.
- [ ] Empty/near-empty PDF pages are flagged as "likely scanned, OCR not supported", not silently summarized.
- [ ] Large spreadsheets/documents are truncated with a note rather than pasted wholesale into context.

## Script

See [scripts/extract_text.py](./scripts/extract_text.py).
