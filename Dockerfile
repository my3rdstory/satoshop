# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      pkg-config \
      libffi-dev \
      libcairo2 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libpangoft2-1.0-0 \
      libgdk-pixbuf-2.0-0 \
      libxml2 \
      libxslt1.1 \
      libjpeg62-turbo \
      libpng16-16 \
      libwebp7 \
      libtiff6 \
      libpq5 \
      shared-mime-info \
      fonts-noto-cjk \
      fontconfig \
      locales \
      ca-certificates \
      curl \
      git && \
    echo "ko_KR.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=ko_KR.UTF-8 \
    LC_ALL=ko_KR.UTF-8

FROM base AS builder

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

FROM base AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=satoshop.settings \
    PYTHONPATH=/app \
    EXPERT_FONT_DIR=/app/expert/static/expert/fonts \
    OSFONTDIR=/app/expert/static/expert/fonts:/usr/share/fonts/truetype/noto \
    RUN_MIGRATIONS=true \
    RUN_COLLECTSTATIC=true \
    RUN_SYSTEM_CHECK=false

WORKDIR /app

COPY --from=builder /app /app
RUN chmod +x scripts/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["scripts/docker-entrypoint.sh"]
CMD ["gunicorn"]
