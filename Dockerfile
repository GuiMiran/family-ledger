FROM node:22-alpine AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa tesseract-ocr-cat tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
ENV OMP_THREAD_LIMIT=1
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .
COPY --from=web /web/dist ./web/dist
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
