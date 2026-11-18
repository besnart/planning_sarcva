"""Importe un export JSON produit par `exporter_donnees`.

Usage :
    python manage.py importer_donnees fichier.json [--vider]

--vider supprime d'abord toutes les donnees de planning (affectations,
disponibilites, fermetures, etiquettes, journal, praticiens) avant l'import.
Aucune synchronisation automatique : l'import est manuel et ponctuel.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from planning.models import (
    Affectation,
    Disponibilite,
    EtiquetteBloc,
    Fermeture,
    JournalGeneration,
    Praticien,
)

MODELES_PLANNING = [Affectation, Disponibilite, Fermeture, EtiquetteBloc,
                    JournalGeneration, Praticien]


class Command(BaseCommand):
    help = "Importe un export JSON (transfert manuel vers une instance hors ligne)."

    def add_arguments(self, parser):
        parser.add_argument("fichier")
        parser.add_argument("--vider", action="store_true",
                            help="Supprime les donnees de planning existantes avant l'import.")

    def handle(self, *args, **options):
        if options["vider"]:
            for modele in MODELES_PLANNING:
                modele.objects.all().delete()
            self.stdout.write("Données de planning précédentes supprimées.")
        call_command("loaddata", options["fichier"])
        self.stdout.write(self.style.SUCCESS(
            f"Import terminé depuis {options['fichier']} (import manuel, aucune synchro)."
        ))
