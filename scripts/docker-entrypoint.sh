#!/usr/bin/env bash
set -euo pipefail

bool_true() {
  case "${1:-true}" in
    [Tt][Rr][Uu][Ee]|[Yy][Ee][Ss]|1|on|ON|On|TRUE|True|"" ) return 0 ;;
    *) return 1 ;;
  esac
}

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-satoshop.settings}"
export PORT="${PORT:-8000}"
export EXPERT_FONT_DIR="${EXPERT_FONT_DIR:-/app/expert/static/expert/fonts}"
export OSFONTDIR="${OSFONTDIR:-/app/expert/static/expert/fonts:/usr/share/fonts/truetype/noto}"

if [ -f scripts/render_setup_signer.sh ]; then
  # shellcheck disable=SC1091
  . scripts/render_setup_signer.sh
fi

if bool_true "${RUN_MIGRATIONS:-true}"; then
  echo "🔄 Running database migrations..."
  uv run python manage.py migrate --noinput
fi

if bool_true "${RUN_COLLECTSTATIC:-true}"; then
  echo "🧱 Collecting static files..."
  uv run python manage.py collectstatic --noinput --clear
fi

if bool_true "${RUN_SYSTEM_CHECK:-true}"; then
  echo "✅ Running Django system checks..."
  uv run python manage.py check --deploy
fi

if [ "$#" -eq 0 ] || [ "$1" = "gunicorn" ]; then
  CMD=(
    uv run gunicorn satoshop.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --log-level "${GUNICORN_LOG_LEVEL:-info}"
  )
else
  CMD=("$@")
fi

exec "${CMD[@]}"
