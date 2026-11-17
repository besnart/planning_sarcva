#!/usr/bin/env bash
# Lance le planning SARCVA sans ligne de commande : installe, initialise, ouvre le navigateur.
# Usage : double-clic ou ./start.sh   (PORT=8000 par defaut, DEMO_PASSWORD pour le mot de passe de demo)
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creation de l'environnement virtuel..."
  python3 -m venv .venv
fi
. .venv/bin/activate

echo "Installation des dependances..."
pip install -q -r requirements.txt

python manage.py migrate --noinput

if [ ! -f db.sqlite3 ]; then
  if [ -z "$DEMO_PASSWORD" ]; then
    DEMO_PASSWORD=demo
    echo "Mot de passe de demo : demo (a changer via la variable DEMO_PASSWORD)"
  fi
  echo "Creation des donnees de demonstration..."
  DEMO_PASSWORD="$DEMO_PASSWORD" python manage.py init_demo
fi

PORT="${PORT:-8000}"
echo "Lancement sur http://localhost:$PORT/ (Ctrl+C pour arreter)"
(sleep 3; python -m webbrowser "http://localhost:$PORT/") >/dev/null 2>&1 &
python manage.py runserver "0.0.0.0:$PORT"
