FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image processing and OCR
# - tesseract-ocr: Required for pytesseract (OCR functionality)
# - tesseract-ocr-eng: English language pack for Tesseract
# - libgl1: OpenGL library (required by opencv-python headless)
# - libglib2.0-0: GLib library (required by some image processing libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run the application
# Use PORT environment variable (Railway sets this automatically)
# Default to 8000 if PORT is not set
CMD sh -c "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"

