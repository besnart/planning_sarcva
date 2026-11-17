#!/usr/bin/env bash
# Linux : double-clic ou ./start.sh lance le planning et ouvre le navigateur
# une fois le serveur pret. Necessite Python 3.12+.
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3.12 ou plus est requis : installez-le (ex. sudo apt install python3) puis relancez."
  exit 1
fi

exec "$PY" start.py
