# ── Stage 1: Builder ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps for building native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY . .

# Install all deps (including optional)
RUN pip install --no-cache-dir -e ".[full]"


# ── Stage 2: Runtime ─────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps for runtime: ffmpeg (Whisper), tesseract (OCR), curl (healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /build /app/backend

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create data directories
RUN mkdir -p /app/data/chroma /app/data/mem0

# Run as non-root user
RUN useradd -m -s /bin/bash crimescope && \
    chown -R crimescope:crimescope /app
USER crimescope

# Health check
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5001/api/v1/health/ping || exit 1

EXPOSE 5001

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "5001", "--workers", "2"]
