# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

COPY frontend/ ./
# Empty VITE_API_URL = same-origin /api requests
ENV VITE_API_URL=
RUN npm run build

# Stage 2: Python app with embedded frontend
FROM python:3.12-slim

WORKDIR /app

# Install uv (reliable install method)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -b /usr/local/bin \
    && apt-get remove -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Backend
COPY backend/ ./
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Copy built frontend into static dir
COPY --from=frontend-builder /app/frontend/dist ./static

# Create non-root user (App Runner requirement)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app
ENV STATIC_DIR=/app/static

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
