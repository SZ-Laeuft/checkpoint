# --- Builder Stage ---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_HTTP_TIMEOUT=300

# Install build dependencies for spidev and other C-extension based packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Final Stage ---
FROM python:3.13-slim-bookworm

WORKDIR /app

# 1. Create the 'spi' group with GID 999 (common on RPi OS)
# 2. Create appuser and add to the spi group
RUN groupadd -g 999 spi && \
    useradd -r -m -g spi appuser

COPY --from=builder --chown=appuser:spi /app /app

ENV PATH="/app/.venv/bin:$PATH"

# Note: In some cases, you might need to run as root if group permissions
# aren't sufficient, but try appuser first for security.
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]