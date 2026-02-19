"""
Remove all searchable text from a PDF, leaving only images.
Produces an image-only (scanned-like) PDF with no text layer.

Usage:
    uv run python scripts/remove_searchable_text.py <input.pdf> [output.pdf]
"""

import sys
from pathlib import Path

import fitz

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def remove_searchable_text(input_path: Path, output_path: Path | None = None) -> None:
    """Strip text layer from PDF, keep images only."""
    output_path = output_path or input_path
    doc = fitz.open(input_path)

    for page in doc:
        # Redact entire page - removes text, keeps images
        page.add_redact_annot(page.rect)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    # Save to temp first if overwriting input
    if output_path.resolve() == input_path.resolve():
        output_path = input_path.parent / f".{input_path.name}.tmp"
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    if output_path.suffix == ".tmp":
        output_path.replace(input_path)
        print(f"Saved: {input_path}")
    else:
        print(f"Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/remove_searchable_text.py <input.pdf> [output.pdf]")
        sys.exit(1)
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else inp
    if not inp.exists():
        print(f"Error: {inp} not found")
        sys.exit(1)
    remove_searchable_text(inp, out)
