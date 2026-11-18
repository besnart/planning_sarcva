"""Cree un jeu de donnees de demonstration : praticiens, comptes et planning genere.

Usage :
    python manage.py init_demo [--annee 2026] [--quadrimestre 1] [--sans-planning]

Le mot de passe des comptes de demo est lu dans la variable d'environnement
DEMO_PASSWORD (a definir obligatoirement pour un deploiement reel).
"""

import datetime as dt
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from planning.attribution import generer_quadrimestre
from planning.models import (
    NIVEAU_ADMINISTRATEUR,
    NIVEAU_SUPERADMINISTRATEUR,
    NIVEAU_UTILISATEUR,
    Praticien,
)

DEMO_PRATICIENS = [
    ("Dr Aubert", 100, "L", False),
    ("Dr Bernard", 100, "P", False),
    ("Dr Caron", 100, "L", True),
    ("Dr Durand", 80, "P", False),
    ("Dr Esteve", 100, "L", False),
    ("Dr Fabre", 100, "P", True),
    ("Dr Garnier", 60, "P", False),
    ("Dr Henry", 100, "L", False),
    ("Dr Ibiza", 100, "P", False),
    ("Dr Joly", 50, "P", False),
    ("Dr Klein", 100, "L", False),
    ("Dr Lambert", 80, "P", False),
]


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration (praticiens, comptes, planning)."

    def add_arguments(self, parser):
        today = timezone.localdate()
        parser.add_argument("--annee", type=int, default=today.year)
        parser.add_argument("--quadrimestre", type=int,
                            default=(today.month - 1) // 4 + 1, choices=[1, 2, 3])
        parser.add_argument("--sans-planning", action="store_true",
                            help="Ne génère pas le planning automatique.")
        parser.add_argument("--password", default=os.environ.get("DEMO_PASSWORD"),
                            help="Mot de passe des comptes de démo (ou env DEMO_PASSWORD).")

    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            self.stdout.write(self.style.WARNING(
                "Aucun mot de passe fourni : définissez DEMO_PASSWORD ou --password."
            ))
            return

        compte_admin, cree = User.objects.get_or_create(username="admin")
        if cree:
            compte_admin.set_password(password)
            compte_admin.is_superuser = True
            compte_admin.is_staff = True
            compte_admin.save()

        for nom, quote, type_p, dj in DEMO_PRATICIENS:
            user = None
            if nom == "Dr Aubert":
                user = compte_admin
            elif nom in ("Dr Bernard", "Dr Caron"):
                username = nom.split()[-1].lower()
                user, cree = User.objects.get_or_create(username=username)
                if cree:
                    user.set_password(password)
                    user.save()
            praticien, cree = Praticien.objects.get_or_create(
                nom=nom,
                defaults={
                    "user": user,
                    "quote_part": quote,
                    "type": type_p,
                    "dj": dj,
                    "niveau": NIVEAU_SUPERADMINISTRATEUR if nom == "Dr Aubert"
                    else NIVEAU_UTILISATEUR,
                },
            )
            if cree:
                self.stdout.write(f"Praticien créé : {nom} ({quote} %, type {type_p}, DJ={dj})")

        if not options["sans_planning"]:
            journal = generer_quadrimestre(options["annee"], options["quadrimestre"],
                                            auteur=compte_admin)
            nb = len([l for l in journal.avertissements.splitlines() if l.strip()])
            self.stdout.write(self.style.SUCCESS(
                f"Planning Q{options['quadrimestre']} {options['annee']} généré "
                f"({nb} poste(s) non pourvu(s))."
            ))
        self.stdout.write(self.style.SUCCESS("Jeu de démonstration prêt."))
