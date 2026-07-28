#!/usr/bin/env sh
set -e

python manage.py migrate --noinput
python manage.py ensure_admin
python manage.py seed_if_empty
python manage.py sync_product_photos
python manage.py sync_deliveroo_drinks
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
