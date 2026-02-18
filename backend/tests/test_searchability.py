"""Helpers and tests for PDF searchability verification."""

import fitz


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text


def assert_pdf_is_searchable(pdf_bytes: bytes) -> None:
    """Assert that PDF has extractable text (searchable)."""
    text = extract_text_from_pdf(pdf_bytes)
    assert len(text.strip()) > 0, f"PDF has no extractable text, got: {repr(text[:100])}"
