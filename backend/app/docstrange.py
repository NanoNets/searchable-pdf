from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings

DOCSTRANGE_BASE_URL = "https://extraction-api.nanonets.com"
EXTRACT_SYNC_PATH = "/api/v1/extract/sync"


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
    page: int
    normalized: bool = True


@dataclass
class BoundingBoxElement:
    content: str
    page: int
    bounding_box: BoundingBox
    markdown_line: int = 0
    word_offset: int = 0


@dataclass
class PageDimension:
    page: int
    width: float
    height: float


@dataclass
class ExtractResult:
    markdown_content: str
    elements: list[BoundingBoxElement]
    page_dimensions: list[PageDimension]


class DocstrangeError(Exception):
    """Raised when Docstrange API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _parse_bounding_box(data: dict[str, Any] | None) -> BoundingBox:
    data = data or {}
    return BoundingBox(
        x=float(data.get("x", 0)),
        y=float(data.get("y", 0)),
        width=float(data.get("width", 0)),
        height=float(data.get("height", 0)),
        page=int(data.get("page", 1)),
        normalized=data.get("normalized", True),
    )


def _parse_element(data: dict[str, Any]) -> BoundingBoxElement:
    bbox_data = data.get("bounding_box") or {}
    return BoundingBoxElement(
        content=data.get("content", ""),
        page=int(data.get("page", 1)),
        bounding_box=_parse_bounding_box(bbox_data),
        markdown_line=int(data.get("markdown_line", 0)),
        word_offset=int(data.get("word_offset", 0)),
    )


def _parse_page_dimensions(data: dict[str, Any]) -> list[PageDimension]:
    pages = data.get("pages", [])
    return [
        PageDimension(
            page=int(p.get("page", i + 1)),
            width=float(p.get("width", 0)),
            height=float(p.get("height", 0)),
        )
        for i, p in enumerate(pages)
    ]


def extract_with_bboxes(pdf_bytes: bytes, filename: str) -> ExtractResult:
    """
    Call Docstrange sync extraction API with word-level bounding boxes.
    Returns markdown content, word elements with coordinates, and page dimensions.
    """
    settings = get_settings()

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{DOCSTRANGE_BASE_URL}{EXTRACT_SYNC_PATH}",
            headers={"Authorization": f"Bearer {settings.nanonets_api_key}"},
            files={"file": (filename, pdf_bytes, "application/pdf")},
            data={
                "output_format": "markdown",
                "include_metadata": "bounding_boxes_word",
            },
        )

    if response.status_code == 401:
        raise DocstrangeError("Invalid or missing API key", status_code=401)
    if response.status_code == 429:
        raise DocstrangeError("Rate limit exceeded", status_code=429)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise DocstrangeError(
            f"Docstrange API error: {detail}",
            status_code=response.status_code,
        )

    body = response.json()

    if not body.get("success"):
        raise DocstrangeError(
            body.get("message", "Extraction failed"),
            status_code=400,
        )

    if body.get("status") == "failed":
        raise DocstrangeError(
            body.get("message", "Extraction failed"),
            status_code=400,
        )

    result = body.get("result", {})
    markdown_data = result.get("markdown", {})
    markdown_content = markdown_data.get("content", "")

    metadata = markdown_data.get("metadata", {})
    bboxes_data = metadata.get("bounding_boxes")

    if not bboxes_data:
        raise DocstrangeError(
            "No bounding boxes in response. Ensure include_metadata=bounding_boxes_word is supported.",
            status_code=400,
        )

    if not bboxes_data.get("success"):
        raise DocstrangeError(
            "Bounding box extraction was not successful",
            status_code=400,
        )

    elements_data = bboxes_data.get("elements", [])
    elements = [
        _parse_element(el)
        for el in elements_data
        if el.get("bounding_box")  # Skip elements without coordinates (e.g. images)
    ]

    page_dimensions_data = bboxes_data.get("page_dimensions", {})
    page_dimensions = _parse_page_dimensions(page_dimensions_data)

    return ExtractResult(
        markdown_content=markdown_content,
        elements=elements,
        page_dimensions=page_dimensions,
    )
