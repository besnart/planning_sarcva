"""Services metier : contraintes obligatoires, affectation, statistiques."""

import datetime as dt

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from .creneaux import (
    APREM,
    DEMI,
    JOURNEE,
    MATIN,
    NUIT,
    Poste,
    dates_quadrimestre,
    postes_lies,
    postes_pour_date,
)
from .jours_feries import est_jour_ouvrable
from .models import Affectation, Disponibilite, Fermeture, EtiquetteBloc, Praticien

SECTIONS_GARDE_ASTREINTE = {"REANIMATION", "ASTREINTE"}


def sections_fermees(date: dt.date) -> set:
    return set(Fermeture.objects.filter(date=date).values_list("section", flat=True))


def etiquettes(date: dt.date) -> dict:
    return dict(EtiquetteBloc.objects.filter(date=date).values_list("code", "etiquette"))


def postes_date(date: dt.date, avec_fermetures: bool = True):
    """Postes affichables pour une date, fermetures prises en compte par defaut."""
    fermees = sections_fermees(date) if avec_fermetures else ()
    return postes_pour_date(date, sections_fermees=fermees)


def affectations_date(date: dt.date) -> dict:
    """cle (section, code, part, index) -> praticien pour une date."""
    return {
        (a.section, a.code, a.part, a.index): a.praticien
        for a in Affectation.objects.filter(date=date).select_related("praticien")
    }


def chevauche(part_a: str, part_b: str) -> bool:
    """Deux vacations se chevauchent-elles le meme jour ?"""
    if part_a == NUIT or part_b == NUIT:
        return False
    if part_a in (JOURNEE, DEMI) or part_b in (JOURNEE, DEMI):
        return True
    return part_a == part_b


def _paire_vendredi_dimanche(date: dt.date, section: str, code: str):
    """Date jumelle pour les regles vendredi -> dimanche (garde et astreinte)."""
    if section == "REANIMATION" and code == "GARDE":
        if date.weekday() == 4:
            return date + dt.timedelta(days=2)
        if date.weekday() == 6:
            return date - dt.timedelta(days=2)
    if section == "ASTREINTE":
        if date.weekday() == 4:
            return date + dt.timedelta(days=2)
        if date.weekday() == 6:
            return date - dt.timedelta(days=2)
    return None


def est_indisponible(praticien: Praticien, date: dt.date, part: str) -> bool:
    indispo = Disponibilite.objects.filter(
        praticien=praticien, date=date, disponible=False
    ).values_list("part", flat=True)
    for p in indispo:
        if p == JOURNEE or chevauche(p, part):
            return True
    return False


def verifier_contraintes(date, cle, praticien, ignorer_cle=None, contexte=None) -> list:
    """Regles OBLIGATOIRES. Retourne la liste des erreurs (vide si conforme).

    `contexte` (optionnel) : {"affectations": [...], "garde_astreinte_veille": set(ids)}
    pour eviter des requetes repetees pendant la generation automatique.
    """
    erreurs = []
    section, code, part, index = cle
    postes = {p.cle: p for p in postes_pour_date(date)}
    poste = postes.get(cle)
    if poste is None:
        return ["Créneau inconnu pour cette date."]
    if not poste.assignable:
        return ["Aucune personne ne doit être postée sur ce créneau ce jour-là."]
    if poste.exige_dj and not praticien.dj:
        return ["Seul un praticien étiqueté DJ peut être posté en Réanimation DJ."]

    if contexte is not None:
        autres = [
            a for a in contexte["affectations"]
            if a.praticien_id == praticien.id
            and (a.section, a.code, a.part, a.index) != ignorer_cle
        ]
    else:
        autres = [
            a for a in Affectation.objects.filter(date=date, praticien=praticien)
            if (a.section, a.code, a.part, a.index) != ignorer_cle
        ]

    # Regle CA : une personne en CA ne peut etre postee ailleurs (et inversement).
    en_ca = any(a.section == "CA" for a in autres)
    if section == "CA":
        if any(a.section != "CA" for a in autres):
            erreurs.append("Posté en CA : aucune autre poste le même jour (règle obligatoire).")
    elif en_ca:
        erreurs.append("Déjà posté en CA ce jour : aucun autre poste possible (règle obligatoire).")

    # Une seule vacation de travail par jour (postes lies d'un meme groupe exceptes).
    if section not in ("AI", "CA"):
        groupes = {p.cle: p.groupe for p in postes_pour_date(date)}
        for a in autres:
            if a.section in ("AI", "CA"):
                continue
            g_a = groupes.get((a.section, a.code, a.part, a.index), f"unique:{a.pk}")
            if g_a != poste.groupe:
                erreurs.append(f"Déjà posté sur {a.section}/{a.code} ce jour-là.")

    # Regle AI : pas de poste sur un créneau equivalent le meme jour.
    if section == "AI":
        for a in autres:
            if a.section not in ("AI", "CA") and chevauche(part, a.part):
                erreurs.append(f"Conflit avec {a.section}/{a.code} : créneau équivalent (règle AI).")
    else:
        for a in autres:
            if a.section == "AI" and chevauche(part, a.part):
                erreurs.append(f"Conflit avec AI {a.part} : créneau équivalent le même jour (règle obligatoire).")

    # Regle : pas de poste le lendemain d'une garde ou d'une astreinte.
    if section != "CA":
        if contexte is not None:
            a_garde_veille = praticien.id in contexte["garde_astreinte_veille"]
        else:
            veille = date - dt.timedelta(days=1)
            a_garde_veille = Affectation.objects.filter(
                date=veille, praticien=praticien
            ).filter(Q(section="ASTREINTE") | Q(section="REANIMATION", code="GARDE")).exists()
        if a_garde_veille:
            erreurs.append("Posté en garde/astreinte la veille : aucun poste le lendemain (règle obligatoire).")

    # Regles vendredi -> dimanche (garde et astreinte, meme personne).
    paire = _paire_vendredi_dimanche(date, section, code)
    if paire is not None and code in ("GARDE", "AST"):
        jumelle = Affectation.objects.filter(date=paire, section=section, code=code).first()
        if jumelle is not None and jumelle.praticien_id != praticien.id:
            erreurs.append(
                f"La personne postée le vendredi en {code} doit être la même le dimanche "
                f"({paire}) (règle obligatoire)."
            )
    return erreurs


@transaction.atomic
def assigner(date, cle, praticien, contextes=None):
    """Affecte (ou des-affecte si praticien=None) un poste, en propageant aux postes lies
    (meme personne) et a la date jumelle vendredi/dimanche. Retourne (ok, erreurs).

    `contextes` : dict date -> contexte pour verifier_contraintes (optionnel)."""
    postes = {p.cle: p for p in postes_pour_date(date)}
    poste = postes.get(cle)
    if poste is None:
        return False, ["Créneau inconnu pour cette date."]
    if praticien is not None and not poste.assignable:
        return False, ["Aucune personne ne doit être postée sur ce créneau ce jour-là."]

    cibles = [(date, poste)]
    for lie in postes_lies(date, poste):
        cibles.append((date, lie))
    paire = _paire_vendredi_dimanche(date, poste.section, poste.code)
    if paire is not None:
        for p in postes_pour_date(paire):
            if p.section == poste.section and p.code == poste.code:
                cibles.append((paire, p))

    if praticien is not None:
        erreurs = []
        for d, p in cibles:
            ctx = contextes.get(d) if contextes else None
            erreurs += verifier_contraintes(d, p.cle, praticien, ignorer_cle=p.cle, contexte=ctx)
        if erreurs:
            return False, sorted(set(erreurs))

    for d, p in cibles:
        Affectation.objects.filter(
            date=d, section=p.section, code=p.code, part=p.part, index=p.index
        ).delete()
        if praticien is not None:
            Affectation.objects.create(
                date=d, section=p.section, code=p.code, part=p.part,
                index=p.index, praticien=praticien,
            )
    return True, []


def periode_stats(echelle: str, annee: int, mois: int = None, quadrimestre: int = None):
    """(debut, fin, libelle) pour une echelle mois / quadrimestre / annee."""
    if echelle == "mois":
        mois = mois or 1
        debut = dt.date(annee, mois, 1)
        fin = dt.date(annee + (mois == 12), (mois % 12) + 1, 1) - dt.timedelta(days=1)
        return debut, fin, f"{debut.strftime('%B %Y')}"
    if echelle == "quadrimestre":
        q = quadrimestre or 1
        dates = dates_quadrimestre(annee, q)
        return dates[0], dates[-1], f"Q{q} {annee}"
    return dt.date(annee, 1, 1), dt.date(annee, 12, 31), f"Année {annee}"


def _poste_lookup(date):
    return {p.cle: p for p in postes_pour_date(date)}


def stats_praticien(praticien: Praticien, debut: dt.date, fin: dt.date) -> dict:
    affectations = Affectation.objects.filter(
        praticien=praticien, date__gte=debut, date__lte=fin
    )
    heures = 0.0
    journees = 0.0
    for a in affectations:
        poste = _poste_lookup(a.date).get((a.section, a.code, a.part, a.index))
        if poste is not None:
            heures += poste.heures
            journees += poste.fraction_journee
    return {"heures": heures, "journees": journees}


def charge_travail(praticien: Praticien, debut: dt.date, fin: dt.date) -> float:
    """Heures de travail effectuees (hors CA) — sert a l'equite d'attribution."""
    affectations = Affectation.objects.filter(
        praticien=praticien, date__gte=debut, date__lte=fin
    ).exclude(section="CA")
    heures = 0.0
    for a in affectations:
        poste = _poste_lookup(a.date).get((a.section, a.code, a.part, a.index))
        if poste is not None:
            heures += poste.heures
    return heures


def stats_par_poste(debut: dt.date, fin: dt.date) -> list:
    """Totaux par poste (section/code) sur la periode."""
    lignes = {}
    for a in Affectation.objects.filter(date__gte=debut, date__lte=fin):
        poste = _poste_lookup(a.date).get((a.section, a.code, a.part, a.index))
        if poste is None:
            continue
        cle = (poste.section, poste.code)
        if cle not in lignes:
            lignes[cle] = {"label": poste.label, "section": poste.section, "code": poste.code,
                           "heures": 0.0, "journees": 0.0, "effectif": 0}
        lignes[cle]["heures"] += poste.heures
        lignes[cle]["journees"] += poste.fraction_journee
        lignes[cle]["effectif"] += 1
    return sorted(lignes.values(), key=lambda l: (l["section"], l["code"]))


def stats_totales(debut: dt.date, fin: dt.date) -> dict:
    lignes = stats_par_poste(debut, fin)
    return {
        "heures": sum(l["heures"] for l in lignes),
        "journees": sum(l["journees"] for l in lignes),
        "affectations": sum(l["effectif"] for l in lignes),
    }


def est_jour_ouvrable_service(date: dt.date) -> bool:
    return est_jour_ouvrable(date)
