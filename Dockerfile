# Field Shift in one image: MongoDB + API + front.
#   docker build -t field-shift .
#   docker run --rm -p 8000:8000 field-shift        # http://localhost:8000
# MongoDB listens only inside the container. Add `-v field-shift-db:/data/db` to keep the database.
FROM mongo:7

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH=/app/.venv/bin:$PATH \
    FIELD_SHIFT_MONGO_URI=mongodb://127.0.0.1:27017 \
    FIELD_SHIFT_DB=field_shift

WORKDIR /app

# Dependencies first, so this layer is rebuilt only when the lock file changes.
COPY pyproject.toml uv.lock ./
RUN uv python install 3.12 && uv sync --frozen --no-dev --no-install-project

COPY field_shift/ field_shift/
COPY data/ data/
COPY docs/*.html docs/
COPY web/ web/
COPY docker/entrypoint.sh /usr/local/bin/field-shift-entrypoint

RUN useradd --system --no-create-home app \
    && mkdir -p data/v2 \
    && chown -R app data/v2 \
    && chmod +x /usr/local/bin/field-shift-entrypoint

EXPOSE 8000
VOLUME /data/db
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

ENTRYPOINT ["field-shift-entrypoint"]
