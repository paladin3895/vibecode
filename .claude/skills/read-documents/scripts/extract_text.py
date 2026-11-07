#!/usr/bin/env python3
"""Extract readable Markdown from .docx, .xlsx/.xls, or .pdf files.

Usage:
    python extract_text.py <path-to-file> [--max-rows N]

Prints Markdown to stdout. Supported formats:
    .docx          -> python-docx
    .xlsx / .xls   -> pandas + openpyxl
    .pdf           -> pdfplumber (text-based PDFs only, no OCR)
"""
import argparse
import sys
from pathlib import Path

# Maps the name Python reports in ModuleNotFoundError to the pip package
# that provides it (they don't always match, e.g. `docx` -> `python-docx`).
_MODULE_TO_PACKAGE = {
    "docx": "python-docx",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "pdfplumber": "pdfplumber",
    "tabulate": "tabulate",  # used internally by DataFrame.to_markdown()
}


def extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    lines = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower() if para.style else ""
        if style.startswith("heading"):
            digits = "".join(ch for ch in style if ch.isdigit()) or "1"
            lines.append(f"{'#' * int(digits)} {text}")
        else:
            lines.append(text)

    for table in doc.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        if not rows:
            continue
        header, *body = rows
        lines.append("")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in body:
            lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def extract_xlsx(path: Path, max_rows: int) -> str:
    import pandas as pd

    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    lines = []

    for name, df in sheets.items():
        lines.append(f"## {name}")
        if len(df) > max_rows:
            lines.append(f"_(showing first {max_rows} of {len(df)} rows)_")
            df = df.head(max_rows)
        lines.append(df.to_markdown(index=False))
        lines.append("")

    return "\n".join(lines)


def extract_pdf(path: Path) -> str:
    import pdfplumber

    lines = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            lines.append(f"## Page {i}")
            text = (page.extract_text() or "").strip()
            lines.append(
                text if text else "_(no extractable text — page may be scanned/image-only)_"
            )

            for table in page.extract_tables() or []:
                if not table:
                    continue
                header, *body = table
                header = [cell or "" for cell in header]
                lines.append("")
                lines.append("| " + " | ".join(header) + " |")
                lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                for row in body:
                    lines.append("| " + " | ".join(cell or "" for cell in row) + " |")

            lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--max-rows",
        type=int,
        default=200,
        help="Max rows per sheet before truncation (xlsx only, default: 200)",
    )
    args = parser.parse_args()

    suffix = args.path.suffix.lower()
    try:
        if suffix == ".docx":
            output = extract_docx(args.path)
        elif suffix in (".xlsx", ".xls"):
            output = extract_xlsx(args.path, args.max_rows)
        elif suffix == ".pdf":
            output = extract_pdf(args.path)
        else:
            sys.exit(f"Unsupported file type: {suffix} (supported: .docx, .xlsx, .xls, .pdf)")
    except ModuleNotFoundError as exc:
        package = _MODULE_TO_PACKAGE.get(exc.name, exc.name)
        sys.exit(
            f"Missing dependency '{exc.name}'. Install it in this same Python "
            f"environment with:\n\n    pip install {package}\n\n"
            "(On Windows, if 'pip' isn't recognized, use 'py -m pip install "
            f"{package}' or '<path-to-python.exe> -m pip install {package}' "
            "for the interpreter you're running this script with.)"
        )

    print(output)


if __name__ == "__main__":
    main()
