FROM python:3.11-slim

WORKDIR /app/backend
COPY . .
RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app
WORKDIR /app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "5001"]
