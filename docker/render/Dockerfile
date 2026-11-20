FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-mapnik python3-gdal python3-psycopg2 python3-yaml python3-requests python3-numpy python3-scipy python3-opencv python3-pil \
      gdal-bin osm2pgsql osmium-tool postgresql-client git curl ca-certificates unzip nodejs npm \
      fonts-noto-core fonts-noto-cjk fonts-noto-hinted fonts-noto-unhinted fonts-hanazono fonts-unifont \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g carto@1.2.0
ARG CARTO_VERSION=v5.9.0
RUN git clone --depth 1 --branch ${CARTO_VERSION} https://github.com/gravitystorm/openstreetmap-carto.git /opt/openstreetmap-carto
WORKDIR /opt/openstreetmap-carto
RUN ln -s /usr/share/fonts fonts && carto project.mml > mapnik.xml
# The repo is mounted at /work (same relative paths as the host); mapdig runs from source.
ENV CARTO_VERSION=${CARTO_VERSION} CARTO_DIR=/opt/openstreetmap-carto \
    PYTHONPATH=/work/src HOME=/tmp PYTHONDONTWRITEBYTECODE=1
RUN printf '#!/bin/sh\nexec python3 -m mapdig "$@"\n' > /usr/local/bin/mapdig && chmod +x /usr/local/bin/mapdig
WORKDIR /work
