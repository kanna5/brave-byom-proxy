FROM python:3.12-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy

COPY . /app

RUN <<-EOF
    set -xe
    apk update
    apk add binutils
    cd /app
    uv sync --no-managed-python
    uv run python -m compileall -j$(nproc) .
    find . -type f \( -name '*.so' -or -name '*.so.*' \) -exec strip '{}' +
EOF

FROM python:3.12-alpine

COPY --from=builder /app /app
RUN python -m compileall -j$(nproc)

USER nobody
WORKDIR /app

ENTRYPOINT [ "./.venv/bin/fastapi", "run", "main.py" ]
