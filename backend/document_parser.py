"""Extract plain text from PDF (PyMuPDF) or TXT files."""

from pathlib import Path

import fitz  # PyMuPDF


def extract_text(file_path: Path, suffix: str) -> str:
    suffix_lower = suffix.lower().lstrip(".")
    if suffix_lower == "pdf":
        doc = fitz.open(file_path)
        try:
            parts: list[str] = []
            for page in doc:
                parts.append(page.get_text())
            return "\n".join(parts).strip()
        finally:
            doc.close()
    if suffix_lower == "txt":
        return file_path.read_text(encoding="utf-8", errors="replace").strip()
    raise ValueError(f"Unsupported file type: {suffix_lower}")
