"""Command-line utility to process PDFs via the Searchable PDF API."""

import argparse
import sys
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a scanned PDF to searchable PDF via the API.",
        epilog="Example: searchable-pdf document.pdf -o searchable.pdf",
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the PDF file to process",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path for searchable PDF (default: searchable_<input>.pdf)",
    )
    parser.add_argument(
        "-u",
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )
    args = parser.parse_args()

    input_path = args.file.resolve()
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1
    if not input_path.suffix.lower() == ".pdf":
        print("Error: File must be a PDF", file=sys.stderr)
        return 1

    output_path = args.output
    if output_path is None:
        output_path = input_path.parent / f"searchable_{input_path.name}"
    output_path = output_path.resolve()

    base_url = args.url.rstrip("/")
    process_url = f"{base_url}/process"

    if not args.quiet:
        print(f"Processing: {input_path}")
        print(f"API: {process_url}")

    try:
        with open(input_path, "rb") as f:
            files = {"file": (input_path.name, f, "application/pdf")}
            with httpx.Client(timeout=120.0) as client:
                response = client.post(process_url, files=files)
    except httpx.ConnectError as e:
        print(f"Error: Could not connect to API at {base_url}", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        print("  Make sure the service is running: uv run uvicorn app.main:app --port 8000", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if response.status_code != 200:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        print(f"Error: API returned {response.status_code}", file=sys.stderr)
        print(f"  {detail}", file=sys.stderr)
        return 1

    output_path.write_bytes(response.content)
    if not args.quiet:
        print(f"Saved: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
