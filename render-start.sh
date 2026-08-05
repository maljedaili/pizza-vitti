#!/usr/bin/env sh
set -e

python manage.py migrate --noinput
python manage.py ensure_admin
python manage.py seed_if_empty
python manage.py sync_product_photos
python manage.py sync_deliveroo_menu
python manage.py sync_drinks_page
python manage.py sync_review_sources
if [ -n "${GOOGLE_BUSINESS_CLIENT_ID:-}" ] && [ -n "${GOOGLE_BUSINESS_CLIENT_SECRET:-}" ] && [ -n "${GOOGLE_BUSINESS_REFRESH_TOKEN:-}" ]; then
  python manage.py sync_google_reviews || echo "Google review synchronization will be retried from the owner dashboard."
fi
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
