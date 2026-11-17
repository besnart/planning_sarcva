@echo off
rem Windows : double-cliquer ce fichier lance le planning et ouvre le navigateur
rem une fois le serveur pret. Necessite Python 3.12+ (python.org, cocher "Add python.exe to PATH").
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if "%PY%"=="" (
  where python >nul 2>nul && set "PY=python"
)
if "%PY%"=="" (
  echo Python 3.12 ou plus est requis pour lancer le planning.
  echo Telechargez-le sur https://www.python.org/downloads/ en cochant "Add python.exe to PATH".
  start https://www.python.org/downloads/
  pause
  exit /b 1
)

%PY% start.py

echo.
echo Le serveur est arrete. Appuyez sur une touche pour fermer cette fenetre.
pause
