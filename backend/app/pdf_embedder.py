import io

import fitz

from app.docstrange import BoundingBoxElement, ExtractResult


def _get_page_content_rect(page: fitz.Page) -> fitz.Rect:
    """
    Get the bounding rect of page content (typically the scanned image).
    Falls back to page.rect if no content found.
    """
    images = page.get_images()
    if images:
        # Use first image placement as content area (scanned PDFs usually have one image)
        img_rects = page.get_image_rects(images[0][0])
        if img_rects:
            return img_rects[0]
    return page.rect


def _get_page_dimensions(doc: fitz.Document) -> dict[int, tuple[float, float]]:
    """Get (width, height) for each page (1-based index)."""
    dims: dict[int, tuple[float, float]] = {}
    for i in range(len(doc)):
        page = doc[i]
        rect = page.rect
        dims[i + 1] = (rect.width, rect.height)
    return dims


def _get_page_content_bounds(doc: fitz.Document) -> dict[int, fitz.Rect]:
    """Get content rect (image area) for each page (1-based index)."""
    bounds: dict[int, fitz.Rect] = {}
    for i in range(len(doc)):
        bounds[i + 1] = _get_page_content_rect(doc[i])
    return bounds


def _normalized_to_pdf_point(
    x: float, y: float, width: float, height: float,
    content_rect: fitz.Rect,
) -> tuple[float, float]:
    """
    Convert Docstrange normalized coords (0-1, y=0 at top) to PDF point (x, baseline_y).
    Uses content_rect (image area) for mapping - Docstrange coords are relative to content.
    """
    # Map normalized (0-1) to content rect
    pdf_x = content_rect.x0 + x * content_rect.width
    # Both Docstrange and PyMuPDF insert_text/TextWriter use top-left origin.
    # Baseline at bottom of bbox: y + height from top, no flip needed.
    content_height = content_rect.height
    baseline_y = content_rect.y0 + (y + height) * content_height
    return (pdf_x, baseline_y)


def _font_size_from_height(height_norm: float, page_height: float) -> float:
    """Derive font size from normalized bounding box height."""
    size = height_norm * page_height
    return max(4.0, min(size, 72.0))  # Clamp between 4 and 72 pt


def embed_text_layer(
    input_pdf_bytes: bytes,
    elements: list[BoundingBoxElement],
) -> bytes:
    """
    Embed invisible searchable text at word positions in the PDF.
    Uses normalized bounding boxes and actual PDF page dimensions.
    """
    doc = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    pdf_dims = _get_page_dimensions(doc)

    # Use actual PDF page dimensions for coordinate conversion
    for page_num, (page_width, page_height) in pdf_dims.items():
        page = doc[page_num - 1]
        page.clean_contents()  # Normalize content stream so overlay works

        page_elements = [e for e in elements if e.page == page_num]
        # Sort by markdown_line, word_offset if available for reading order
        page_elements.sort(key=lambda e: (e.markdown_line, e.word_offset))

        content_rect = _get_page_content_rect(page)

        tw = fitz.TextWriter(content_rect)
        font = fitz.Font("helv")

        for el in page_elements:
            bbox = el.bounding_box
            point = _normalized_to_pdf_point(
                bbox.x, bbox.y, bbox.width, bbox.height,
                content_rect,
            )
            fontsize = _font_size_from_height(bbox.height, content_rect.height)

            if not el.content.strip():
                continue

            try:
                tw.append(
                    fitz.Point(point[0], point[1]),
                    el.content,
                    font=font,
                    fontsize=fontsize,
                )
            except Exception:
                pass

        tw.write_text(page, render_mode=3, overlay=True)

    buffer = io.BytesIO()
    doc.save(buffer, garbage=4, deflate=True)
    doc.close()
    return buffer.getvalue()


def embed_text_layer_from_result(
    input_pdf_bytes: bytes,
    result: ExtractResult,
) -> bytes:
    """Convenience wrapper that takes ExtractResult directly."""
    return embed_text_layer(input_pdf_bytes, result.elements)
