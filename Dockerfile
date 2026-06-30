# syntax=docker/dockerfile:1
# Build for arm64 home-lab nodes:
#   docker buildx build --platform linux/arm64 \
#     -t docker.io/wilgrimthepilgrim/rk-terminauto:latest --push .
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# uv settings: copy (not symlink) into the venv, and don't try to manage Python.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    LOG_FORMAT=json \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (cached unless lockfile changes).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then the application code.
COPY poll.py ./

# Run as a non-root user.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "poll.py"]
