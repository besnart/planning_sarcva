#!/usr/bin/env python3
"""Lanceur visuel du planning SARCVA.

Installe les dépendances, crée la base et les données de démo si besoin,
lance le serveur, puis ouvre le navigateur UNIQUEMENT quand le serveur répond.

Lancement : double-clic via start.bat / start.command / start.sh, ou :
    python start.py
Variables d'environnement : PORT (8000 par défaut), DEMO_PASSWORD.
"""

import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = os.environ.get("PORT", "8000")
URL = f"http://localhost:{PORT}/"
VENV = ROOT / ".venv"


def python_du_venv() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def nb_praticiens() -> int:
    out = subprocess.run(
        [sys.executable, "manage.py", "shell", "-c",
         "from planning.models import Praticien; print(Praticien.objects.count())"],
        cwd=ROOT, capture_output=True, text=True,
    )
    try:
        return int(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return -1


def main() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass
    if Path(sys.prefix).resolve() != VENV.resolve():
        if not python_du_venv().exists():
            print("Création de l'environnement virtuel...")
            subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
        print("Relance dans l'environnement virtuel...")
        os.execv(str(python_du_venv()), [str(python_du_venv()), str(Path(__file__).resolve())])

    os.chdir(ROOT)

    print("Installation des dépendances...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"])

    print("Préparation de la base de données...")
    subprocess.check_call([sys.executable, "manage.py", "migrate", "--noinput"])

    if nb_praticiens() == 0:
        if "DEMO_PASSWORD" not in os.environ:
            os.environ["DEMO_PASSWORD"] = "demo"
            print("Mot de passe des comptes de démo : demo "
                  "(définir DEMO_PASSWORD avant le lancement pour le changer)")
        print("Création des données de démonstration (cela peut prendre une minute)...")
        subprocess.check_call([sys.executable, "manage.py", "init_demo"])

    print(f"Lancement du serveur sur {URL} ...")
    serveur = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"0.0.0.0:{PORT}", "--noreload"],
        cwd=ROOT,
    )
    try:
        for _ in range(120):
            if serveur.poll() is not None:
                print("ERREUR : le serveur s'est arrêté immédiatement.")
                print("Le port est peut-être déjà utilisé : relancez avec PORT=8001")
                sys.exit(1)
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
                break
            except Exception:
                time.sleep(1)
        else:
            print(f"Le serveur met du temps à répondre ; ouvrez manuellement : {URL}")
        print(f"Le serveur répond : ouverture du navigateur sur {URL}")
        webbrowser.open(URL)
        print("Planning lancé. Laissez cette fenêtre ouverte ; Ctrl+C pour arrêter.")
        serveur.wait()
    except KeyboardInterrupt:
        serveur.terminate()


if __name__ == "__main__":
    main()
