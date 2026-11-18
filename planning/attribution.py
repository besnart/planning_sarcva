"""Attribution automatique des postes par quadrimestre.

Regles OBLIGATOIRES (jamais violees) : CA exclusif, conflit AI sur créneau
équivalent, pas de poste le lendemain d'une garde/astreinte, meme personne
vendredi->dimanche pour garde et astreinte, DJ réservé aux étiquetés DJ.

Regles IDEALES (tente de les respecter) : répartition homogene selon la
quote-part (100 % = 1747 h/an), "L" privilegies sur les blocs, réanimation
autour des gardes de week-end, Réanimation 4 la semaine précédant une garde.

Apres generation, toute modification manuelle reste possible (admin).
"""

import datetime as dt
import random

from django.db import transaction
from django.db.models import Q

from .creneaux import JOURNEE, dates_quadrimestre, postes_pour_date, quadrimestres
from .models import (
    Affectation,
    Disponibilite,
    EtiquetteBloc,
    JournalGeneration,
    Praticien,
    etiquette_bloc_par_defaut,
)
from .services import (
    assigner,
    charge_travail,
    chevauche,
    sections_fermees,
    verifier_contraintes,
)

POSTES_MANUELS = {"AI", "CA"}

# Ordre de remplissage au sein d'une journee (les plus contraints d'abord).
ORDRE_SECTIONS = [
    "REANIMATION",
    "ASTREINTE",
    "BLOC",
    "CPA",
    "CONSULTATION",
    "REGULATION",
    "KT",
]


def _postes_a_remplir(date: dt.date, fermee: set) -> list:
    postes = postes_pour_date(date, sections_fermees=fermee)
    postes = [p for p in postes if p.assignable and p.section not in POSTES_MANUELS]
    postes.sort(
        key=lambda p: (
            ORDRE_SECTIONS.index(p.section) if p.section in ORDRE_SECTIONS else 99,
            p.code,
            p.part,
        )
    )
    return postes


def _cible_quadrimestre(praticien: Praticien) -> float:
    return max(praticien.heures_annuelles_cible() * 4 / 12, 1.0)


def _score(praticien, poste, date, charge, rng, gardes_par_date) -> float:
    score = (charge + poste.heures) / _cible_quadrimestre(praticien)
    # Regle ideale : les "L" sont privilegies sur les blocs.
    if poste.section == "BLOC" and praticien.type == "L":
        score -= 0.10
    # Regles ideales liees aux gardes : réanimation autour du week-end de garde.
    if poste.section == "REANIMATION":
        veille = date - dt.timedelta(days=1)
        lendemain = date + dt.timedelta(days=1)
        if gardes_par_date.get(veille) == praticien.id or gardes_par_date.get(lendemain) == praticien.id:
            score -= 0.15
    # Regle ideale : Réanimation 4 la semaine précédant une garde.
    if poste.code == "REA4":
        if any(
            gardes_par_date.get(date + dt.timedelta(days=j)) == praticien.id
            for j in range(1, 8)
        ):
            score -= 0.10
    score += rng.random() * 0.01
    return score


def _candidats(date, poste, praticiens, charges, contexte, indispo_par_date, rng, gardes_par_date):
    scores = []
    for praticien in praticiens:
        indispo = indispo_par_date.get(date, {}).get(praticien.id, [])
        if any(p == JOURNEE or chevauche(p, poste.part) for p in indispo):
            continue
        if poste.exige_dj and not praticien.dj:
            continue
        if verifier_contraintes(date, poste.cle, praticien, contexte=contexte):
            continue
        scores.append(
            (_score(praticien, poste, date, charges[praticien.id], rng, gardes_par_date),
             praticien)
        )
    scores.sort(key=lambda t: t[0])
    return [p for _, p in scores]


@transaction.atomic
def generer_quadrimestre(annee: int, trimestre: int, auteur=None) -> JournalGeneration:
    if trimestre not in quadrimestres():
        raise ValueError("Quadrimestre invalide (1, 2 ou 3).")
    dates = dates_quadrimestre(annee, trimestre)
    debut, fin = dates[0], dates[-1]

    # La generation remplace les affectations automatiques du quadrimestre,
    # mais conserve les postes manuels AI et CA.
    Affectation.objects.filter(date__gte=debut, date__lte=fin).exclude(
        section__in=POSTES_MANUELS
    ).delete()

    # Etiquettes par defaut des blocs (bloc 4 : CEC le mercredi, CONGENITAL sinon).
    for date in dates:
        for code in ("BLOC1", "BLOC2", "BLOC3", "BLOC4", "BLOC5", "BLOC6"):
            EtiquetteBloc.objects.get_or_create(
                date=date,
                code=code,
                defaults={"etiquette": etiquette_bloc_par_defaut(date, code) or "CEC"},
            )

    praticiens = list(Praticien.objects.all())
    charges = {p.id: charge_travail(p, debut, fin) for p in praticiens}
    indispo_par_date = {}
    for d in Disponibilite.objects.filter(date__gte=debut, date__lte=fin, disponible=False):
        indispo_par_date.setdefault(d.date, {}).setdefault(d.praticien_id, []).append(d.part)
    rng = random.Random(f"{annee}-Q{trimestre}")
    avertissements = []
    gardes_par_date = {}
    contextes = {}
    garde_astreinte_veille = set()

    for date in dates:
        fermee = sections_fermees(date)
        contexte = {
            "affectations": list(Affectation.objects.filter(date=date)),
            "garde_astreinte_veille": garde_astreinte_veille,
        }
        contextes[date] = contexte
        for poste in _postes_a_remplir(date, fermee):
            deja = next(
                (a for a in contexte["affectations"]
                 if (a.section, a.code, a.part, a.index) == poste.cle),
                None,
            )
            if deja is not None:
                charges[deja.praticien_id] = charges.get(deja.praticien_id, 0.0) + poste.heures
                if poste.section == "REANIMATION" and poste.code == "GARDE":
                    gardes_par_date[date] = deja.praticien_id
                continue
            place = False
            for candidat in _candidats(date, poste, praticiens, charges, contexte,
                                        indispo_par_date, rng, gardes_par_date):
                ok, _erreurs = assigner(date, poste.cle, candidat, contextes=contextes)
                if ok:
                    charges[candidat.id] = charges.get(candidat.id, 0.0) + poste.heures
                    contexte["affectations"] = list(Affectation.objects.filter(date=date))
                    if poste.section == "REANIMATION" and poste.code == "GARDE":
                        gardes_par_date[date] = candidat.id
                    place = True
                    break
            if not place:
                avertissements.append(
                    f"{date} : aucun candidat pour {poste.label_complet} "
                    f"({poste.section}/{poste.code})"
                )
        garde_astreinte_veille = set(
            Affectation.objects.filter(date=date)
            .filter(Q(section="ASTREINTE") | Q(section="REANIMATION", code="GARDE"))
            .values_list("praticien_id", flat=True)
        )

    return JournalGeneration.objects.create(
        annee=annee,
        quadrimestre=trimestre,
        auteur=auteur,
        avertissements="\n".join(avertissements),
    )
