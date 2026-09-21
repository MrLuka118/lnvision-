# syntax=docker/dockerfile:1.7
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

# Tailwind standalone CLI lives outside the bind-mounted source tree.
ENV TAILWIND_CLI_PATH=/opt/tailwind
COPY . .
RUN DJANGO_SETTINGS_MODULE=config.settings.dev DJANGO_SECRET_KEY=build \
    DATABASE_URL=postgres://build@localhost/build python manage.py tailwind download_cli

RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown -R app:app /app /data /opt/tailwind
USER app

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
