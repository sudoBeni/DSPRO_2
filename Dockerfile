FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./


RUN UV_NO_CACHE=1 uv sync --frozen --no-editable

COPY . .

WORKDIR /app/src

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV UV_NO_CACHE=1

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=10s --timeout=25s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
