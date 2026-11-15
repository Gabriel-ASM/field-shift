# Field Shift in one image: MongoDB + API + front (ctrlaltespaco, built in the first stage).
#   docker build -t field-shift .
#   docker run --rm -p 8000:8000 field-shift        # http://localhost:8000
# MongoDB listens only inside the container. Add `-v field-shift-db:/data/db` to keep the database.
# `--build-arg FIELD_SHIFT_VERSION=<commit>` stamps the front and the API with the build (GET /config `version`);
# without it both say "dev", which never asks a tab to reload.
FROM node:22-slim AS front
WORKDIR /front
COPY ctrlaltespaco/package.json ctrlaltespaco/package-lock.json ./
RUN npm ci
COPY ctrlaltespaco/ ./
ARG FIELD_SHIFT_VERSION=dev
ENV FIELD_SHIFT_VERSION=$FIELD_SHIFT_VERSION
RUN npm run build

FROM mongo:7 AS base

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/app/.venv/bin:$PATH \
    FIELD_SHIFT_MONGO_URI=mongodb://127.0.0.1:27017 \
    FIELD_SHIFT_DB=field_shift \
    FIELD_SHIFT_WEB_DIR=/app/ctrlaltespaco/dist

WORKDIR /app

# Dependencies first, so this layer is rebuilt only when the lock file changes.
COPY pyproject.toml uv.lock ./
RUN uv python install 3.12 && uv sync --frozen --no-dev --no-install-project

COPY field_shift/ field_shift/
COPY data/catalog/ data/catalog/
COPY data/contracts/ data/contracts/
COPY data/geo/ data/geo/
COPY data/pipeline/ data/pipeline/
COPY data/policies/ data/policies/
COPY data/profiles/ data/profiles/
COPY data/reference/ data/reference/
COPY data/v2/ data/v2/
COPY docs/*.html docs/
COPY --from=front /front/dist ctrlaltespaco/dist
COPY docker/entrypoint.sh /usr/local/bin/field-shift-entrypoint

RUN useradd --system --no-create-home app \
    && mkdir -p data/v2 \
    && chown -R app data/v2 \
    && chmod +x /usr/local/bin/field-shift-entrypoint

# Last, so a new commit does not rebuild the layers above.
ARG FIELD_SHIFT_VERSION=dev
ENV FIELD_SHIFT_VERSION=$FIELD_SHIFT_VERSION

EXPOSE 8000
VOLUME /data/db
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

ENTRYPOINT ["field-shift-entrypoint"]

# Development image: the product plus the whole repository (research, downloads, raw data, earlier pages)
# browsable at /reference.   docker build --target dev -t field-shift:dev .
FROM base AS dev
COPY . /app/reference/
ENV FIELD_SHIFT_REFERENCE_DIR=/app/reference

# Default target: the product only.
FROM base AS production
