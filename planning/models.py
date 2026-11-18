import datetime as dt

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from .creneaux import (
    APREM,
    MATIN,
    SECTIONS,
    ETIQUETTES_BLOC,
    etiquette_bloc_par_defaut,
)

NIVEAU_VISIONNAGE = "VISIONNAGE"
NIVEAU_UTILISATEUR = "UTILISATEUR"
NIVEAU_ADMIN = "ADMINISTRATEUR"
NIVEAU_SUPERADMIN = "SUPERADMINISTRATEUR"

NIVEAUX = [
    (NIVEAU_VISIONNAGE, "Visionnage"),
    (NIVEAU_UTILISATEUR, "Utilisateur"),
    (NIVEAU_ADMIN, "Administrateur"),
    (NIVEAU_SUPERADMIN, "Super Administrateur"),
]
ORDRE_NIVEAUX = {
    NIVEAU_VISIONNAGE: 1,
    NIVEAU_UTILISATEUR: 2,
    NIVEAU_ADMIN: 3,
    NIVEAU_SUPERADMIN: 4,
}

NIVEAU_ADMINISTRATEUR = NIVEAU_ADMIN
NIVEAU_SUPERADMINISTRATEUR = NIVEAU_SUPERADMIN


class Praticien(models.Model):
    TYPE_P = "P"
    TYPE_L = "L"
    TYPES = [(TYPE_P, "P"), (TYPE_L, "L")]

    nom = models.CharField("Nom", max_length=100, unique=True)
    user = models.OneToOneField(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="praticien", verbose_name="Compte associé",
    )
    quote_part = models.PositiveIntegerField(
        "Quote-part (%)", default=100,
        help_text="100 % correspond à 1747 h sur l'année.",
    )
    type = models.CharField("Type", max_length=1, choices=TYPES, default=TYPE_P)
    dj = models.BooleanField("Étiqueté DJ", default=False,
                             help_text="Seul un praticien DJ peut être posté en Réanimation DJ.")
    niveau = models.CharField("Accréditation", max_length=20, choices=NIVEAUX,
                              default=NIVEAU_VISIONNAGE)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Praticien"
        verbose_name_plural = "Praticiens"

    def __str__(self):
        return self.nom

    def heures_annuelles_cible(self) -> float:
        return self.quote_part / 100 * settings.HEURES_ANNUELLES_100

    def a_niveau(self, niveau: str) -> bool:
        return ORDRE_NIVEAUX[self.niveau] >= ORDRE_NIVEAUX[niveau]


class Disponibilite(models.Model):
    JOURNEE = "journee"
    PARTS = [(MATIN, "Matin"), (APREM, "Après-midi"), (JOURNEE, "Journée")]

    praticien = models.ForeignKey(Praticien, on_delete=models.CASCADE,
                                  related_name="disponibilites")
    date = models.DateField()
    part = models.CharField(max_length=10, choices=PARTS, default=JOURNEE)
    disponible = models.BooleanField(default=False)

    class Meta:
        unique_together = [("praticien", "date", "part")]
        ordering = ["date", "part"]

    def __str__(self):
        etat = "disponible" if self.disponible else "indisponible"
        return f"{self.praticien} - {self.date} ({self.part}) : {etat}"


class Affectation(models.Model):
    """Une personne postee sur un créneau pour une date."""

    date = models.DateField()
    section = models.CharField(max_length=20, choices=[(s, s) for s in SECTIONS])
    code = models.CharField(max_length=20)
    part = models.CharField(max_length=10)
    index = models.PositiveIntegerField(default=0)
    praticien = models.ForeignKey(Praticien, on_delete=models.CASCADE,
                                  related_name="affectations")

    class Meta:
        unique_together = [("date", "section", "code", "part", "index")]
        ordering = ["date", "section", "code", "part", "index"]
        verbose_name = "Affectation"
        verbose_name_plural = "Affectations"

    def __str__(self):
        return f"{self.date} {self.section}/{self.code}/{self.part}[{self.index}] -> {self.praticien}"

    def clean(self):
        from .services import verifier_contraintes
        erreurs = verifier_contraintes(self.date, (self.section, self.code, self.part, self.index),
                                       self.praticien, ignorer_cle=(self.section, self.code, self.part, self.index))
        if erreurs:
            raise ValidationError(erreurs)


class Fermeture(models.Model):
    """Section fermee pour une date : aucune personne postee."""

    date = models.DateField()
    section = models.CharField(max_length=20, choices=[(s, s) for s in SECTIONS])

    class Meta:
        unique_together = [("date", "section")]
        ordering = ["date", "section"]

    def __str__(self):
        return f"{self.date} : {self.section} fermee"


class EtiquetteBloc(models.Model):
    """Étiquette d'activite d'un bloc pour une date (CEC, LASER, ...)."""

    date = models.DateField()
    code = models.CharField(max_length=10)  # BLOC1 .. BLOC6
    etiquette = models.CharField(max_length=20, choices=[(e, e) for e in ETIQUETTES_BLOC])

    class Meta:
        unique_together = [("date", "code")]
        ordering = ["date", "code"]

    def __str__(self):
        return f"{self.date} {self.code} : {self.etiquette}"

    def save(self, *args, **kwargs):
        if not self.etiquette:
            self.etiquette = etiquette_bloc_par_defaut(self.date, self.code)
        super().save(*args, **kwargs)


class JournalGeneration(models.Model):
    """Trace des generations automatiques par quadrimestre."""

    annee = models.PositiveIntegerField()
    quadrimestre = models.PositiveIntegerField(choices=[(1, "Q1 (janv.-avr.)"),
                                                        (2, "Q2 (mai-août)"),
                                                        (3, "Q3 (sept.-déc.)")])
    auteur = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    date_creation = models.DateTimeField(auto_now_add=True)
    avertissements = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return f"Génération Q{self.quadrimestre} {self.annee} par {self.auteur}"
