"""Jours feries legaux francais, calcules sans dependance externe."""

import datetime as dt


def _paques(annee: int) -> dt.date:
    """Dimanche de Paques (algorithme gregorien anonyme)."""
    a = annee % 19
    b, c = divmod(annee, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois, jour = divmod(h + l - 7 * m + 114, 31)
    return dt.date(annee, mois, jour + 1)


def jours_feries(annee: int) -> set[dt.date]:
    paques = _paques(annee)
    return {
        dt.date(annee, 1, 1),    # Jour de l'an
        paques + dt.timedelta(days=1),    # Lundi de Paques
        dt.date(annee, 5, 1),    # Fete du Travail
        dt.date(annee, 5, 8),    # Victoire 1945
        paques + dt.timedelta(days=39),   # Ascension
        paques + dt.timedelta(days=50),   # Lundi de Pentecote
        dt.date(annee, 7, 14),   # Fete nationale
        dt.date(annee, 8, 15),   # Assomption
        dt.date(annee, 11, 1),   # Toussaint
        dt.date(annee, 11, 11),  # Armistice 1918
        dt.date(annee, 12, 25),  # Noel
    }


def est_ferie(date: dt.date) -> bool:
    return date in jours_feries(date.year)


def est_jour_ouvrable(date: dt.date) -> bool:
    """Lundi a vendredi, hors jours feries."""
    return date.weekday() < 5 and not est_ferie(date)
