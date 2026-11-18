#!/bin/sh
# Demarrage du conteneur heberge : migrations, eventuel seed de demo, gunicorn.
# Variables attendues (fournies par la plateforme) : HOST, PORT, DATABASE_URL.
# Optionnelles : SEED_DEMO=1 + DEMO_PASSWORD pour creer les donnees de demo,
# DJANGO_SECRET_KEY (obligatoire en production), CSRF_TRUSTED_ORIGINS.
set -e
cd /app

python manage.py migrate --noinput

if [ "$SEED_DEMO" = "1" ]; then
  echo "Seed de demonstration (comptes admin/bernard/caron, mot de passe = DEMO_PASSWORD)"
  python manage.py init_demo
fi

exec gunicorn config.wsgi:application \
  --bind "${HOST:-0.0.0.0}:${PORT:-8000}" \
  --workers 2 --threads 4 --timeout 60
