FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 UV_NO_CACHE=1 UV_LINK_MODE=copy UV_NO_PROGRESS=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN pip install --no-cache-dir uv==0.9.26
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
FROM base AS camera
RUN uv sync --locked --no-dev --no-editable --extra camera
FROM base AS lab
