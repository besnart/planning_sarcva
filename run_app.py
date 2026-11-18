#!/usr/bin/env python3
"""Point d'entree de l'executable autonome planning-sarcva (PyInstaller).

Equivalent de start.py, mais sans avoir besoin de Python installe :
migre la base, cree les donnees de demo si elle est vide, sert l'application
et ouvre le navigateur uniquement quand le serveur repond.

Lancement : double-clic sur planning-sarcva.exe (PORT=8000 par defaut).
"""

import os
import threading
import time
import urllib.request
import webbrowser

PORT = os.environ.get("PORT", "8000")


def ouvrir_quand_pret():
    for _ in range(180):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
            webbrowser.open(f"http://localhost:{PORT}/")
            print(f"Navigateur ouvert sur http://localhost:{PORT}/")
            return
        except Exception:
            time.sleep(1)
    print(f"Serveur en ligne ; ouvrez http://localhost:{PORT}/ dans votre navigateur.")


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.core.management import call_command

    print("Préparation de la base de données...")
    call_command("migrate", interactive=False)

    from planning.models import Praticien

    if Praticien.objects.count() == 0:
        os.environ.setdefault("DEMO_PASSWORD", "demo")
        print("Mot de passe des comptes de démo : demo "
              "(définir DEMO_PASSWORD avant le lancement pour le changer)")
        print("Création des données de démonstration (une minute environ)...")
        call_command("init_demo")

    print(f"Lancement du serveur sur http://localhost:{PORT}/ ...")
    threading.Thread(target=ouvrir_quand_pret, daemon=True).start()
    call_command("runserver", f"0.0.0.0:{PORT}", use_reloader=False)


if __name__ == "__main__":
    main()
