"""
Calibration pipeline: Generate a PDF with text at known positions,
run it through Docstrange, embed the text back, and compare positions.

Usage:
    uv run python tests/calibrate.py
"""

import json
import sys
from pathlib import Path

import fitz

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.docstrange import extract_with_bboxes
from app.pdf_embedder import _normalized_to_pdf_point

PAGE_WIDTH = 612  # Letter
PAGE_HEIGHT = 792

# Known text positions: (text, x_pt, y_pt, fontsize)
# These use PDF coordinates (bottom-left origin)
KNOWN_WORDS = [
    ("TOP-LEFT", 50, 50, 14),         # near top-left
    ("TOP-RIGHT", 450, 50, 14),       # near top-right
    ("CENTER", 250, 396, 18),         # center of page
    ("BOTTOM-LEFT", 50, 740, 14),     # near bottom-left
    ("BOTTOM-RIGHT", 400, 740, 14),   # near bottom-right
    ("HELLO", 100, 200, 24),          # upper area
    ("WORLD", 300, 600, 24),          # lower area
]

OUT_DIR = Path(__file__).parent.parent


def step1_generate_test_pdf() -> bytes:
    """Generate a PDF with text at known positions."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)

    for text, x, y, size in KNOWN_WORDS:
        page.insert_text((x, y), text, fontsize=size, fontname="helv", color=(0, 0, 0))

    # Add grid lines for reference
    for i in range(0, int(PAGE_WIDTH), 100):
        page.draw_line((i, 0), (i, PAGE_HEIGHT), color=(0.8, 0.8, 0.8), width=0.5)
        page.insert_text((i + 2, 15), str(i), fontsize=6, color=(0.5, 0.5, 0.5))
    for i in range(0, int(PAGE_HEIGHT), 100):
        page.draw_line((0, i), (PAGE_WIDTH, i), color=(0.8, 0.8, 0.8), width=0.5)
        page.insert_text((2, i + 8), str(i), fontsize=6, color=(0.5, 0.5, 0.5))

    pdf_bytes = doc.tobytes()
    doc.close()

    path = OUT_DIR / "calibration_input.pdf"
    path.write_bytes(pdf_bytes)
    print(f"[Step 1] Generated test PDF: {path}")
    return pdf_bytes


def step2_extract_bboxes(pdf_bytes: bytes):
    """Send to Docstrange and get word-level bounding boxes."""
    print("[Step 2] Sending to Docstrange API...")
    result = extract_with_bboxes(pdf_bytes, "calibration_input.pdf")
    print(f"  Got {len(result.elements)} elements, {len(result.page_dimensions)} pages")
    return result


def step3_compare_positions(pdf_bytes: bytes, result):
    """Compare Docstrange bbox positions against known positions."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]

    # For non-image PDFs, content_rect = page.rect
    content_rect = page.rect
    print(f"\n[Step 3] Content rect: {content_rect}")
    print(f"  Page rect: {page.rect}")

    # Map known words to expected positions
    known_map = {w[0]: (w[1], w[2], w[3]) for w in KNOWN_WORDS}

    print(f"\n{'Word':<15} {'Known (x,y)':<20} {'API norm (x,y)':<25} {'Computed (x,y)':<20} {'Delta':<15}")
    print("-" * 95)

    for el in result.elements:
        word = el.content.strip()
        bbox = el.bounding_box

        # Compute PDF point using our conversion
        px, py = _normalized_to_pdf_point(
            bbox.x, bbox.y, bbox.width, bbox.height,
            content_rect,
        )

        # Check if this matches a known word
        known = known_map.get(word)
        if known:
            kx, ky, _ = known
            dx = px - kx
            dy = py - ky
            print(
                f"{word:<15} ({kx:>5.1f},{ky:>5.1f})      "
                f"({bbox.x:.3f},{bbox.y:.3f})          "
                f"({px:>5.1f},{py:>5.1f})      "
                f"(dx={dx:>+6.1f}, dy={dy:>+6.1f})"
            )
        else:
            print(
                f"{word:<15} {'N/A':<20} "
                f"({bbox.x:.3f},{bbox.y:.3f})          "
                f"({px:>5.1f},{py:>5.1f})"
            )

    doc.close()


def step4_generate_overlay(pdf_bytes: bytes, result):
    """Generate PDF with both original text (black) and overlay text (red) for visual comparison."""
    from app.pdf_embedder import _font_size_from_height

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    page.clean_contents()
    content_rect = page.rect

    tw = fitz.TextWriter(content_rect)
    font = fitz.Font("helv")

    for el in result.elements:
        bbox = el.bounding_box
        if not el.content.strip():
            continue

        px, py = _normalized_to_pdf_point(
            bbox.x, bbox.y, bbox.width, bbox.height,
            content_rect,
        )
        fontsize = _font_size_from_height(bbox.height, content_rect.height)

        try:
            tw.append(fitz.Point(px, py), el.content, font=font, fontsize=fontsize)
        except Exception:
            pass

    tw.write_text(page, color=(1, 0, 0), overlay=True)

    out_path = OUT_DIR / "calibration_overlay.pdf"
    doc.save(str(out_path), garbage=4, deflate=True)
    doc.close()
    print(f"\n[Step 4] Overlay PDF saved: {out_path}")
    print("  Black text = original known positions")
    print("  Red text = Docstrange bbox -> our coordinate conversion")
    print("  They should overlap if calibration is correct.")


def main():
    settings = get_settings()
    if not settings.nanonets_api_key:
        print("Error: NANONETS_API_KEY not set in .env", file=sys.stderr)
        return 1

    pdf_bytes = step1_generate_test_pdf()
    result = step2_extract_bboxes(pdf_bytes)
    step3_compare_positions(pdf_bytes, result)
    step4_generate_overlay(pdf_bytes, result)

    print("\n[Done] Open calibration_overlay.pdf to visually inspect alignment.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
