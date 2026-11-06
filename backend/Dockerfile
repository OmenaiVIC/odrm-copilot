# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY backend/src ./backend/src

RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -e .

# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --create-home appuser

COPY --from=builder /app/wheels /app/wheels
COPY --from=builder /app/backend/src ./backend/src
COPY pyproject.toml README.md ./
COPY alembic.ini ./
COPY backend/migrations ./backend/migrations

RUN pip install --upgrade pip && \
    pip install --no-cache-dir /app/wheels/*.whl && \
    pip install --no-cache-dir psycopg[binary] alembic && \
    rm -rf /app/wheels

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn odrm.main:app --host 0.0.0.0 --port 8000"]