FROM python:3.13-slim AS base

WORKDIR /app

# Install PDM
RUN pip install --upgrade --no-cache-dir pdm pip

# Copy project files
COPY pyproject.toml pdm.lock* ./
COPY README.md ./
COPY src/ ./src/

# Install dependencies including FastAPI and uvicorn
RUN pdm install --frozen-lockfile --prod --no-editable --no-self
# Build the project
RUN pdm build --no-sdist


# Expose HTTP port
EXPOSE 8000

########################################## Interactive development stage ##########################################
FROM base AS interactive-work

WORKDIR /app

# Install PDM

ENV PYTHONPATH=/app/src:${PYTHONPATH}

RUN pdm install --frozen-lockfile --dev --no-self

########################################## TEST stage ##########################################
FROM base AS test

RUN pdm install --frozen-lockfile --dev --no-self
RUN pdm run pip install --no-cache-dir --prefix=/app/.venv --no-deps --no-warn-script-location dist/*.whl

COPY tests/ ./tests/
RUN pdm run pytest

########################################## Production stage ##########################################
FROM python:3.13-slim AS release

WORKDIR /app

COPY --from=base /app/.venv /app/.venv
COPY --from=base /app/dist /app/dist

# Install system dependencies including curl for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --prefix=/app/.venv --no-deps --no-warn-script-location dist/*.whl

# Health check for HTTP server
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8000//.container/health || exit 1

# Run HTTP server by default
CMD ["/app/.venv/bin/python", "-m", "ch_mcp", "serve", "--port", "8000", "--no-reload"]
