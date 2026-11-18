"""Exporte toutes les donnees du planning en JSON (pour la version hors ligne).

Usage :
    python manage.py exporter_donnees [fichier.json]

Le fichier peut ensuite etre importe dans une autre instance (ex. l'exe hors ligne)
avec `python manage.py importer_donnees fichier.json --vider`.
ATTENTION : l'export contient les comptes utilisateurs et leurs empreintes de mot de
passe — gardez ce fichier prive.
"""

import json

from django.contrib.auth.models import User
from django.core import serializers
from django.core.management.base import BaseCommand

from planning.models import (
    Affectation,
    Disponibilite,
    EtiquetteBloc,
    Fermeture,
    JournalGeneration,
    Praticien,
)

MODELES = [User, Praticien, Disponibilite, Affectation, Fermeture, EtiquetteBloc,
           JournalGeneration]


class Command(BaseCommand):
    help = "Exporte les donnees du planning en JSON (transfert manuel, aucune synchro)."

    def add_arguments(self, parser):
        parser.add_argument("fichier", nargs="?", default="export_planning.json")

    def handle(self, *args, **options):
        fichier = options["fichier"]
        data = []
        for modele in MODELES:
            data += json.loads(serializers.serialize("json", modele.objects.all()))
        with open(fichier, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)
        self.stdout.write(self.style.SUCCESS(
            f"{len(data)} objet(s) exporté(s) dans {fichier} "
            "(fichier privé : il contient les empreintes de mots de passe)."
        ))
