# syntax=docker/dockerfile:1.7
FROM node:22-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY assets ./assets
COPY static ./static
COPY templates ./templates
COPY vite.config.js ./
RUN npm run build

FROM python:3.13-slim-trixie AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# exiftool: lossless GPS removal. gettext: compilemessages. DejaVu: watermark text.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libimage-exiftool-perl gettext curl fontconfig fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
ARG UV_GROUPS="--group dev"
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project ${UV_GROUPS}

COPY . .
COPY --from=frontend /build/static/dist ./static/dist
RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown -R app:app /app /data
USER app

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
