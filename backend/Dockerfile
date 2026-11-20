FROM python:3.12-slim

WORKDIR /app

# system deps for playwright chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# chromium for the WebAutomator tool
RUN pip install --no-cache-dir playwright && \
    playwright install chromium --with-deps || \
    playwright install chromium

COPY . .

RUN mkdir -p workspace memory_data data

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
