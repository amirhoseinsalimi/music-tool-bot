FROM python:3.15.0-slim-bookworm@sha256:0e019bbdfb5d9874cb2389f1c2884b64aa2ac97c99960b5bc521cef978c0617d AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.5.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_HOME=/opt/poetry

RUN apt update \
 && apt install -y --no-install-recommends ffmpeg make curl ca-certificates bash \
 && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - \
 && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/
RUN poetry install --no-interaction --no-ansi --only main

COPY . /app

RUN useradd -ms /bin/bash appuser

ENV DATA_DIR=/data
RUN mkdir -p "${DATA_DIR}" && chown -R appuser:appuser "${DATA_DIR}"
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs
RUN chown -R appuser:appuser /app

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh \
 && chmod +x /entrypoint.sh \
 && chown appuser:appuser /entrypoint.sh

VOLUME ["/data"]

USER appuser

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
