# GPU image: detection methods, training, hosted-model clients. Dependencies come from
# uv.lock (group "ml"); the mapdig source is mounted at /work and run from there.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_INSTALL_DIR=/opt/python UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 UV_CACHE_DIR=/tmp/uv-cache
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-default-groups --group ml --python 3.12 \
    && rm -rf /tmp/uv-cache && chmod -R a+rX /opt/venv /opt/python
ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/work/src HOME=/tmp PYTHONDONTWRITEBYTECODE=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics
RUN printf '#!/bin/sh\nexec python -m mapdig "$@"\n' > /usr/local/bin/mapdig && chmod +x /usr/local/bin/mapdig
WORKDIR /work
