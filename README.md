# Searchable PDF Service

Convert scanned PDFs to natively searchable PDFs using the [Docstrange API](https://docstrange.nanonets.com) (Nanonets). The service extracts text with word-level bounding boxes and embeds invisible text at the correct positions so you can search and copy text using native PDF viewers.

## Project structure

- **backend/** – FastAPI service and CLI
- **frontend/** – React UI for upload, processing, and PDF viewing

## Features

- Upload scanned PDFs (max 5 pages for sync processing)
- Extract text + word-level coordinates via Docstrange API
- Embed invisible searchable text layer at correct positions
- Web UI: drag-and-drop upload, output PDF viewer, search (Ctrl+F)
- CLI for batch processing

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.10+
- Node.js 18+
- [Nanonets/Docstrange API key](https://docstrange.nanonets.com)

## Setup

### Backend

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env and set NANONETS_API_KEY=your_api_key_here
```

### Frontend

```bash
cd frontend
npm install
```

## Running

### Option 1: Full stack (recommended)

Terminal 1 – backend:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 – frontend (proxies API to backend):

```bash
cd frontend
npm run dev
```

- **Frontend**: http://localhost:5173
- **API docs**: http://localhost:8000/docs

### Option 2: Backend only

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend

The UI provides:

- **Left panel**: Upload zone (drag & drop or click to browse), Process button
- **Right panel**: Output PDF viewer and Download button

Use **Ctrl+F** (Cmd+F on Mac) to search within the embedded PDF viewer.

To point the frontend at a different API URL, set `VITE_API_URL` when building, or use the built-in dev proxy (defaults to `http://localhost:8000`).

## API

### POST /process

Upload a PDF and receive a searchable PDF.

**Request**: `multipart/form-data` with `file` = PDF

**Response**: Searchable PDF file (`application/pdf`)

**Status codes**:
- 200: Success, returns PDF
- 400: Invalid file type, too many pages (>5), or extraction failed
- 401: Invalid API key
- 413: File too large (default max 10MB)
- 429: Rate limit exceeded

### GET /health

Readiness check. Returns 503 if `NANONETS_API_KEY` is not configured.

## Configuration

| Variable         | Required | Default | Description                    |
|------------------|----------|---------|--------------------------------|
| NANONETS_API_KEY | Yes      | -       | Docstrange/Nanonets API key    |
| MAX_FILE_SIZE    | No       | 10485760| Max file size in bytes (10MB)  |
| MAX_PAGES        | No       | 5       | Max pages (Docstrange sync limit) |

## CLI Utility

```bash
cd backend
uv run searchable-pdf document.pdf -o output.pdf
```

## Tests

```bash
cd backend
uv sync --extra dev
uv run pytest tests/ -v
```

## Example (curl)

```bash
curl -X POST http://localhost:8000/process \
  -F "file=@scanned-document.pdf" \
  -o searchable-document.pdf
```
