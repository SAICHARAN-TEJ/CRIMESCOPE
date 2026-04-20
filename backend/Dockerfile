# ── Build stage ───────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# ── Runtime stage ─────────────────────────────────────────────────────
FROM python:3.11-slim
LABEL maintainer="CrimeScope <team@crimescope.ai>"

# System deps for FFmpeg, Tesseract, curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -r crimescope && useradd -r -g crimescope crimescope
WORKDIR /opt/app
COPY . .
RUN chown -R crimescope:crimescope /opt/app
USER crimescope

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
