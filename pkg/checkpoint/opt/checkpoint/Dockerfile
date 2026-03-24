# Stage 1: Build the Svelte Frontend
FROM node AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm install
COPY web/ .
RUN npm run build

# Stage 2: Python Backend
FROM python:3.13-slim
WORKDIR /app

# 1. Install system dependencies (This will work now!)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"

# 3. Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

# 4. Copy Python code and static frontend files
COPY . .
COPY --from=frontend-builder /web/build ./static

# 5. Run the app
# Using 'uv run' ensures the virtualenv created by uv is used
CMD ["uv", "run", "python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]