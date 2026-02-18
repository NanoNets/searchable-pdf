"""Integration tests for PDF embedder - verifies searchability."""

from pathlib import Path

import fitz

from app.docstrange import BoundingBox, BoundingBoxElement, ExtractResult
from app.pdf_embedder import embed_text_layer_from_result
from tests.test_searchability import assert_pdf_is_searchable


def _make_test_result(elements: list[BoundingBoxElement]) -> ExtractResult:
    return ExtractResult(
        markdown_content="",
        elements=elements,
        page_dimensions=[],
    )


def _extract_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(p.get_text() for p in doc)
    doc.close()
    return text


def test_embed_produces_searchable_text():
    """Embedded text must be extractable (searchable) from output PDF."""
    # Create minimal 1-page PDF (no text)
    doc = fitz.open()
    doc.new_page(width=612, height=792)  # Letter size
    input_bytes = doc.tobytes()
    doc.close()

    # Element: "Hello" at top-left, normalized coords
    el = BoundingBoxElement(
        content="Hello",
        page=1,
        bounding_box=BoundingBox(
            x=0.1, y=0.1, width=0.1, height=0.02,
            page=1, normalized=True,
        ),
        markdown_line=0,
        word_offset=0,
    )
    result = _make_test_result([el])

    output_bytes = embed_text_layer_from_result(input_bytes, result)
    text = _extract_text(output_bytes)

    assert "Hello" in text, f"Expected 'Hello' in output, got: {repr(text)}"


def test_embed_multiple_words():
    """Multiple words should all be searchable."""
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    input_bytes = doc.tobytes()
    doc.close()

    elements = [
        BoundingBoxElement(
            content="Test",
            page=1,
            bounding_box=BoundingBox(0.1, 0.2, 0.08, 0.02, 1, True),
            markdown_line=0, word_offset=0,
        ),
        BoundingBoxElement(
            content="Word",
            page=1,
            bounding_box=BoundingBox(0.2, 0.2, 0.08, 0.02, 1, True),
            markdown_line=0, word_offset=1,
        ),
    ]
    result = _make_test_result(elements)
    output_bytes = embed_text_layer_from_result(input_bytes, result)
    text = _extract_text(output_bytes)

    assert "Test" in text and "Word" in text, f"Expected both words, got: {repr(text)}"


def test_real_pdf_output_searchable():
    """If output.pdf exists from a prior run, verify it is searchable."""
    output_path = Path(__file__).parent.parent / "output.pdf"
    if not output_path.exists():
        return  # Skip if no prior run
    output_bytes = output_path.read_bytes()
    assert_pdf_is_searchable(output_bytes)
