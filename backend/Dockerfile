FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir playwright && \
    (playwright install chromium --with-deps || playwright install chromium)

# Build context is the project root so `backend` remains an importable package.
COPY backend/ ./backend/
COPY frontend/ ./frontend/

RUN mkdir -p backend/workspace backend/memory_data backend/data

EXPOSE 7777
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:7777/api/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7777"]
