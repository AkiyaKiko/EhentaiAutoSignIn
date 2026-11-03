FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EHENTAI_DATA_DIR=/data \
    TZ=UTC

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md main.py notify.py ./
COPY ehentai/ ./ehentai/
RUN pip install --no-cache-dir . \
    && mkdir /data \
    && chown 1000:1000 /data

USER 1000:1000
ENTRYPOINT ["python", "/app/main.py"]
