import io
from pathlib import Path

import fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.docstrange import DocstrangeError, extract_with_bboxes
from app.pdf_embedder import embed_text_layer_from_result

app = FastAPI(
    title="Searchable PDF Service",
    description="Convert scanned PDFs to searchable PDFs using Docstrange API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def log_api_key():
    from app.config import _BACKEND_ROOT, _ENV_FILES
    settings = get_settings()
    env_used = [str(f) for f in _ENV_FILES if f.exists()]
    print(f"Loading .env from: {env_used or 'none (using env vars)'}", flush=True)
    if settings.nanonets_api_key:
        print("NANONETS_API_KEY is set", flush=True)
    else:
        print(
            "NANONETS_API_KEY not configured. Add NANONETS_API_KEY=your_key to backend/.env (or project root .env)",
            flush=True,
        )


def _validate_pdf(pdf_bytes: bytes) -> None:
    """Validate PDF and page count. Raises HTTPException on failure."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF: {e}") from e

    try:
        page_count = len(doc)
        doc.close()
    except Exception:
        doc.close()
        raise HTTPException(status_code=400, detail="Could not read PDF") from None

    settings = get_settings()
    if page_count > settings.max_pages:
        raise HTTPException(
            status_code=400,
            detail=f"PDF has {page_count} pages. Maximum allowed is {settings.max_pages}.",
        )


@app.get("/health")
async def health():
    """Readiness check."""
    settings = get_settings()
    if not settings.nanonets_api_key:
        raise HTTPException(status_code=503, detail="NANONETS_API_KEY not configured")
    return {"status": "ok"}


@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    """
    Upload a scanned PDF and receive a searchable PDF with embedded text layer.
    """
    settings = get_settings()

    if not settings.nanonets_api_key:
        raise HTTPException(
            status_code=503,
            detail="NANONETS_API_KEY not configured",
        )

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are accepted.",
        )

    pdf_bytes = await file.read()

    # Validate file size
    if len(pdf_bytes) > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_file_size} bytes.",
        )

    _validate_pdf(pdf_bytes)

    try:
        result = extract_with_bboxes(pdf_bytes, file.filename or "document.pdf")
    except DocstrangeError as e:
        if e.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid API key") from e
        if e.status_code == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded") from e
        raise HTTPException(
            status_code=400,
            detail=e.message,
        ) from e

    if not result.elements:
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from the document.",
        )

    output_bytes = embed_text_layer_from_result(pdf_bytes, result)

    output_filename = f"searchable_{Path(file.filename or 'document.pdf').name}"

    return StreamingResponse(
        io.BytesIO(output_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"',
        },
    )
