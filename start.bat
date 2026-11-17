@echo off
rem Windows : double-cliquer ce fichier lance le planning et ouvre le navigateur.
cd /d "%~dp0"

if not exist .venv\Scripts\activate.bat (
  echo Creation de l'environnement virtuel...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installation des dependances...
pip install -q -r requirements.txt

python manage.py migrate --noinput

if not exist db.sqlite3 (
  if "%DEMO_PASSWORD%"=="" set DEMO_PASSWORD=demo
  echo Mot de passe de demo : %DEMO_PASSWORD% ^(a changer via la variable DEMO_PASSWORD^)
  echo Creation des donnees de demonstration...
  python manage.py init_demo
)

if "%PORT%"=="" set PORT=8000
echo Lancement sur http://localhost:%PORT%/ (Ctrl+C pour arreter)
start http://localhost:%PORT%/
python manage.py runserver 0.0.0.0:%PORT%
