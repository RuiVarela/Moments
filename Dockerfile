FROM python:3.11-slim

ARG VERSION=0.1.0

LABEL org.opencontainers.image.title="moments" \
      org.opencontainers.image.description="Minimal self-hosted photo album" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://hub.docker.com/r/ruifilipevarela/moments"

# ffmpeg: video metadata + poster frames.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Non-editable install: package (code + static frontend) lands in site-packages.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && rm -rf src

# Default config: albums at /source (mount read-only), extracted data at /data.
COPY docker/config.json /app/config.json
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && mkdir -p /source /data

ENV MOMENTS_CONFIG=/app/config.json \
    PUID=1000 \
    PGID=1000 \
    PYTHONUNBUFFERED=1

VOLUME ["/data"]
EXPOSE 8000

# No curl in slim; python is enough.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/albums', timeout=4)" || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "-m", "moments"]
