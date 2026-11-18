"""Schema des postes (créneaux) d'une journee, d'apres le cahier des charges.

Chaque poste est identifie par une cle (section, code, part, index) :
- section : REANIMATION, BLOC, CPA, CONSULTATION, REGULATION, KT, ASTREINTE, AI, CA
- code    : ex. REA1, BLOC1, CPA, PR...
- part    : matin / aprem / journee / nuit / demi
- index   : numero de la vacation pour les postes a capacite > 1 (AI, CA)
"""

import datetime as dt
from dataclasses import dataclass, field

from .jours_feries import est_jour_ouvrable

MATIN = "matin"
APREM = "aprem"
JOURNEE = "journee"
NUIT = "nuit"
DEMI = "demi"

SECTIONS = [
    "REANIMATION",
    "BLOC",
    "CPA",
    "CONSULTATION",
    "REGULATION",
    "KT",
    "ASTREINTE",
    "AI",
    "CA",
]

ETIQUETTES_BLOC = ["CEC", "LASER", "CONGENITAL", "STRUCTUREL", "VASCULAIRE"]

NB_VACATIONS_AI = 6   # 3 matin + 3 apres-midi
NB_VACATIONS_CA = 6   # 3 matin + 3 apres-midi


@dataclass(frozen=True)
class Poste:
    """Un créneau affichable pour une date donnee."""

    section: str
    code: str
    part: str
    index: int = 0
    label: str = ""
    heures: float = 0.0
    fraction_journee: float = 0.0
    groupe: str = ""          # postes lies (meme personne), ex. BLOC16
    exige_dj: bool = False
    assignable: bool = True   # False : aucune personne postee (ex. bloc 4 hors mercredi)
    manuel: bool = False      # poste manuellement (AI, CA)

    @property
    def cle(self) -> tuple:
        return (self.section, self.code, self.part, self.index)

    @property
    def label_complet(self) -> str:
        part = {
            MATIN: "matin",
            APREM: "après-midi",
            JOURNEE: "journée",
            NUIT: "nuit",
            DEMI: "demi-journée",
        }[self.part]
        suffixe = f" {self.index + 1}" if self.index else ""
        return f"{self.label} {part}{suffixe}".strip()


@dataclass
class JourneePlanning:
    date: dt.date
    postes: list = field(default_factory=list)
    sections_fermees: set = field(default_factory=set)
    etiquettes: dict = field(default_factory=dict)  # code bloc -> etiquette


def _postes_reanimation(jour_ouvrable: bool) -> list[Poste]:
    postes = []
    if jour_ouvrable:
        postes += [
            Poste("REANIMATION", "REA1", JOURNEE, label="Réanimation 1",
                  heures=10, fraction_journee=1.0, groupe="REA1_GARDE"),
            Poste("REANIMATION", "REA2", JOURNEE, label="Réanimation 2",
                  heures=10, fraction_journee=1.0, groupe="REA2"),
            Poste("REANIMATION", "REA3", JOURNEE, label="Réanimation 3",
                  heures=10, fraction_journee=1.0, groupe="REA3"),
            Poste("REANIMATION", "REA4", DEMI, label="Réanimation 4",
                  heures=5, fraction_journee=0.5, groupe="REA4"),
            Poste("REANIMATION", "READJ", JOURNEE, label="Réanimation DJ",
                  heures=10, fraction_journee=1.0, groupe="READJ", exige_dj=True),
            Poste("REANIMATION", "GARDE", NUIT, label="Réanimation garde",
                  heures=14, fraction_journee=1.0, groupe="REA1_GARDE"),
        ]
    else:
        postes.append(
            Poste("REANIMATION", "GARDE", JOURNEE, label="Réanimation garde",
                  heures=24, fraction_journee=1.0, groupe="GARDE_WEEKEND")
        )
    return postes


def _postes_blocs(date: dt.date) -> list[Poste]:
    postes = []
    for bloc in ("BLOC1", "BLOC6"):
        groupe = "BLOC16" if bloc in ("BLOC1", "BLOC6") else bloc
        postes += [
            Poste("BLOC", bloc, MATIN, label=f"{bloc}", heures=5.5,
                  fraction_journee=0.5, groupe="BLOC16"),
            Poste("BLOC", bloc, APREM, label=f"{bloc}", heures=5.5,
                  fraction_journee=0.5, groupe="BLOC16"),
        ]
    for bloc, groupe in (("BLOC2", "BLOC2"), ("BLOC5", "BLOC5")):
        postes += [
            Poste("BLOC", bloc, MATIN, label=bloc, heures=5.5,
                  fraction_journee=0.5, groupe=groupe),
            Poste("BLOC", bloc, APREM, label=bloc, heures=5.5,
                  fraction_journee=0.5, groupe=groupe),
        ]
    # Bloc 3 : deux personnes differentes ; l'apres-midi est la personne d'astreinte.
    postes += [
        Poste("BLOC", "BLOC3", MATIN, label="BLOC3", heures=5.5,
              fraction_journee=0.5, groupe="BLOC3_M"),
        Poste("BLOC", "BLOC3", APREM, label="BLOC3", heures=5.5,
              fraction_journee=0.5, groupe="BLOC3_AST"),
    ]
    mercredi = date.weekday() == 2
    postes += [
        Poste("BLOC", "BLOC4", MATIN, label="BLOC4", heures=5.5,
              fraction_journee=0.5, groupe="BLOC4", assignable=mercredi),
        Poste("BLOC", "BLOC4", APREM, label="BLOC4", heures=5.5,
              fraction_journee=0.5, groupe="BLOC4", assignable=mercredi),
    ]
    return postes


def _postes_semaine() -> list[Poste]:
    return [
        Poste("CPA", "CPA", MATIN, label="CPA", heures=4, fraction_journee=0.5, groupe="CPA_M"),
        Poste("CPA", "CPA", APREM, label="CPA", heures=4, fraction_journee=0.5, groupe="CPA_A_PR"),
        Poste("CONSULTATION", "PR", MATIN, label="Consultation PR", heures=4,
              fraction_journee=0.5, groupe="CPA_A_PR"),
        Poste("REGULATION", "REG", MATIN, label="Régulation / VPA", heures=5.5,
              fraction_journee=0.5, groupe="REG"),
        Poste("REGULATION", "REG", APREM, label="Régulation / VPA", heures=5.5,
              fraction_journee=0.5, groupe="REG"),
        Poste("KT", "KT", MATIN, label="KT", heures=5.5,
              fraction_journee=0.5, groupe="KT"),
        Poste("KT", "KT", APREM, label="KT", heures=5.5,
              fraction_journee=0.5, groupe="KT"),
        Poste("ASTREINTE", "AST", JOURNEE, label="Astreinte", heures=6,
              fraction_journee=0.5, groupe="BLOC3_AST"),
    ]


def _postes_quotidiens() -> list[Poste]:
    postes = []
    for index in range(NB_VACATIONS_AI // 2):
        postes.append(Poste("AI", "AI", MATIN, index=index, label="AI",
                            heures=0, fraction_journee=0.5, groupe="", manuel=True))
        postes.append(Poste("AI", "AI", APREM, index=index, label="AI",
                            heures=0, fraction_journee=0.5, groupe="", manuel=True))
    for index in range(NB_VACATIONS_CA // 2):
        postes.append(Poste("CA", "CA", MATIN, index=index, label="CA",
                            heures=0, fraction_journee=0.5, groupe="", manuel=True))
        postes.append(Poste("CA", "CA", APREM, index=index, label="CA",
                            heures=0, fraction_journee=0.5, groupe="", manuel=True))
    return postes


def postes_pour_date(date: dt.date, sections_fermees=(), etiquettes=None) -> list[Poste]:
    """Liste des postes d'une date, sections fermees exclues."""
    fermee = set(sections_fermees)
    ouvrable = est_jour_ouvrable(date)
    postes = _postes_reanimation(ouvrable)
    if ouvrable:
        postes += _postes_blocs(date)
        postes += _postes_semaine()
    else:
        postes.append(Poste("ASTREINTE", "AST", JOURNEE, label="Astreinte", heures=12,
                            fraction_journee=1.0, groupe="AST_WEEKEND"))
    postes += _postes_quotidiens()
    return [p for p in postes if p.section not in fermee]


def postes_lies(date: dt.date, poste: Poste, sections_fermees=()) -> list[Poste]:
    """Postes qui doivent avoir la meme personne que `poste` (liens du cahier des charges)."""
    if not poste.groupe:
        return []
    tous = postes_pour_date(date, sections_fermees)
    return [p for p in tous if p.groupe == poste.groupe and p.cle != poste.cle]


def etiquette_bloc_par_defaut(date: dt.date, code: str) -> str:
    if code == "BLOC4":
        return "CEC" if date.weekday() == 2 else "CONGENITAL"
    return ""


def quadrimestres() -> dict:
    """Quadrimestres d'attribution : Q1 = janv.-avr., Q2 = mai-août, Q3 = sept.-déc."""
    return {1: (1, 4), 2: (5, 8), 3: (9, 12)}


def dates_quadrimestre(annee: int, trimestre: int) -> list[dt.date]:
    premier_mois, dernier_mois = quadrimestres()[trimestre]
    premier = dt.date(annee, premier_mois, 1)
    if dernier_mois == 12:
        dernier = dt.date(annee, 12, 31)
    else:
        dernier = dt.date(annee, dernier_mois + 1, 1) - dt.timedelta(days=1)
    dates = []
    courant = premier
    while courant <= dernier:
        dates.append(courant)
        courant += dt.timedelta(days=1)
    return dates


def lundi_de_la_semaine(date: dt.date) -> dt.date:
    return date - dt.timedelta(days=date.weekday())


def semaines_du_mois(annee: int, mois: int) -> list[list[dt.date]]:
    """Semaines (lundi -> dimanche) affichant le mois, debord possible."""
    premier = dt.date(annee, mois, 1)
    if mois == 12:
        dernier = dt.date(annee, 12, 31)
    else:
        dernier = dt.date(annee, mois + 1, 1) - dt.timedelta(days=1)
    debut = lundi_de_la_semaine(premier)
    fin = lundi_de_la_semaine(dernier) + dt.timedelta(days=6)
    semaines = []
    courant = debut
    while courant <= fin:
        semaines.append([courant + dt.timedelta(days=i) for i in range(7)])
        courant += dt.timedelta(days=7)
    return semaines
