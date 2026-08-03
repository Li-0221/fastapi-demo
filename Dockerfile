FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --chown=10001:10001 pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=10001:10001 src ./src
RUN uv sync --frozen --no-dev --no-editable

COPY --chown=10001:10001 alembic.ini ./
COPY --chown=10001:10001 alembic ./alembic

EXPOSE 8000

USER 10001:10001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
