FROM node:25-alpine AS frontend-builder

WORKDIR /app/veritasreason-explorer


COPY veritasreason-explorer/package.json veritasreason-explorer/package-lock.json* ./


RUN npm install


COPY veritasreason-explorer/ ./
RUN npm run build


FROM python:3.14-slim AS runtime

WORKDIR /app

COPY pyproject.toml ./
COPY veritasreason/ ./veritasreason/

COPY --from=frontend-builder /app/veritasreason/static ./veritasreason/static

RUN pip install --no-cache-dir ".[explorer]"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "veritasreason.explorer.app:app", "--host", "0.0.0.0", "--port", "8000"]