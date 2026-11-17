import calendar
import datetime as dt

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.utils import timezone
from django.views.decorators.http import require_POST

from .attribution import generer_quadrimestre as executer_generation
from .creneaux import ETIQUETTES_BLOC, SECTIONS, quadrimestres, semaines_du_mois
from .forms import NiveauForm, PraticienForm
from .jours_feries import est_ferie
from .models import (
    NIVEAU_ADMINISTRATEUR,
    NIVEAU_SUPERADMINISTRATEUR,
    NIVEAU_UTILISATEUR,
    Affectation,
    Disponibilite,
    EtiquetteBloc,
    Fermeture,
    Praticien,
)
from .permissions import exige_niveau, niveau_de, praticien_de, planning_lecture
from .services import (
    affectations_date,
    assigner,
    etiquettes,
    periode_stats,
    postes_date,
    sections_fermees,
    stats_par_poste,
    stats_praticien,
    stats_totales,
)

MOIS_NOMS = [calendar.month_name[m].capitalize() for m in range(1, 13)]


def planning_annee_mois_courant(request):
    today = timezone.localdate()
    return redirect("planning_mois", annee=today.year, mois=today.month)


def _construire_jours(dates):
    jours = []
    for date in dates:
        affectations = affectations_date(date)
        etiquettes_date = etiquettes(date)
        fermetures = sections_fermees(date)
        postes = []
        for poste in postes_date(date):
            postes.append({
                "poste": poste,
                "praticien": affectations.get(poste.cle),
                "etiquette": etiquettes_date.get(poste.code, "") if poste.section == "BLOC" else "",
            })
        jours.append({
            "date": date,
            "postes": postes,
            "fermetures": fermetures,
            "ferie": est_ferie(date),
        })
    return jours


def planning_mois(request, annee: int, mois: int):
    if not planning_lecture(request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), resolve_url(settings.LOGIN_URL))
        raise PermissionDenied

    semaines_dates = semaines_du_mois(annee, mois)
    toutes_dates = [d for semaine in semaines_dates for d in semaine]
    jours_par_date = {j["date"]: j for j in _construire_jours(toutes_dates)}
    semaines = [[jours_par_date[d] for d in semaine] for semaine in semaines_dates]

    niveau = niveau_de(request)
    peut_modifier = request.user.is_authenticated and niveau >= 3
    edit = peut_modifier and request.GET.get("edit") == "1"
    annee_courante = timezone.localdate().year

    return render(request, "planning/planning_mois.html", {
        "annee": annee,
        "mois": mois,
        "mois_nom": MOIS_NOMS[mois - 1],
        "semaines": semaines,
        "annees": range(annee_courante - 1, annee_courante + 2),
        "mois_noms": MOIS_NOMS,
        "aujourdhui": timezone.localdate(),
        "peut_modifier": peut_modifier,
        "edit": edit,
        "praticiens": Praticien.objects.order_by("nom") if edit else [],
        "sections": SECTIONS,
        "etiquettes_bloc": ETIQUETTES_BLOC,
        "quadrimestres": quadrimestres(),
        "trimestre_courant": (timezone.localdate().month - 1) // 4 + 1,
    })


@require_POST
@exige_niveau(NIVEAU_ADMINISTRATEUR)
def modifier_poste(request, annee: int, mois: int):
    date = dt.date.fromisoformat(request.POST["date"])
    cle = (
        request.POST["section"],
        request.POST["code"],
        request.POST["part"],
        int(request.POST.get("index", 0)),
    )
    praticien_id = request.POST.get("praticien_id") or None
    praticien = get_object_or_404(Praticien, pk=praticien_id) if praticien_id else None
    ok, erreurs = assigner(date, cle, praticien)
    if ok:
        messages.success(request, "Poste mis à jour.")
    else:
        for e in erreurs:
            messages.error(request, e)
    return redirect(f"/planning/{date.year}/{date.month}/?edit=1")


@require_POST
@exige_niveau(NIVEAU_ADMINISTRATEUR)
def basculer_fermeture(request, annee: int, mois: int):
    date = dt.date.fromisoformat(request.POST["date"])
    section = request.POST["section"]
    fermeture = Fermeture.objects.filter(date=date, section=section).first()
    if fermeture:
        fermeture.delete()
        messages.success(request, f"Section {section} réouverte le {date}.")
    else:
        Fermeture.objects.create(date=date, section=section)
        messages.success(request, f"Section {section} fermée le {date} (aucune personne postée).")
    return redirect(f"/planning/{date.year}/{date.month}/?edit=1")


@require_POST
@exige_niveau(NIVEAU_ADMINISTRATEUR)
def modifier_etiquette(request, annee: int, mois: int):
    date = dt.date.fromisoformat(request.POST["date"])
    code = request.POST["code"]
    etiquette = request.POST["etiquette"]
    EtiquetteBloc.objects.update_or_create(
        date=date, code=code, defaults={"etiquette": etiquette}
    )
    messages.success(request, f"Étiquette {code} = {etiquette} le {date}.")
    return redirect(f"/planning/{date.year}/{date.month}/?edit=1")


@require_POST
@exige_niveau(NIVEAU_ADMINISTRATEUR)
def generer_quadrimestre(request, annee: int, mois: int):
    annee_gen = int(request.POST["annee"])
    trimestre = int(request.POST["quadrimestre"])
    journal = executer_generation(annee_gen, trimestre, auteur=request.user)
    nb = len([l for l in journal.avertissements.splitlines() if l.strip()])
    if nb:
        messages.warning(request, f"Génération Q{trimestre} {annee_gen} : {nb} poste(s) non pourvu(s).")
    else:
        messages.success(request, f"Planning du quadrimestre Q{trimestre} {annee_gen} généré.")
    premier_mois = quadrimestres()[trimestre][0]
    return redirect("planning_mois", annee=annee_gen, mois=premier_mois)


@exige_niveau(NIVEAU_UTILISATEUR)
def stats(request):
    today = timezone.localdate()
    echelle = request.GET.get("echelle", "mois")
    if echelle not in ("mois", "quadrimestre", "annee"):
        echelle = "mois"
    annee = int(request.GET.get("annee", today.year))
    mois = int(request.GET.get("mois", today.month))
    quadrimestre = int(request.GET.get("quadrimestre", (today.month - 1) // 4 + 1))
    debut, fin, libelle = periode_stats(echelle, annee, mois, quadrimestre)

    lignes_praticiens = []
    for p in Praticien.objects.order_by("nom"):
        s = stats_praticien(p, debut, fin)
        if s["heures"] or s["journees"]:
            lignes_praticiens.append({"praticien": p, **s})
    lignes_praticiens.sort(key=lambda l: -l["heures"])

    return render(request, "planning/stats.html", {
        "echelle": echelle,
        "annee": annee,
        "mois": mois,
        "quadrimestre": quadrimestre,
        "mois_noms": MOIS_NOMS,
        "annees": range(today.year - 1, today.year + 2),
        "libelle": libelle,
        "debut": debut,
        "fin": fin,
        "lignes_praticiens": lignes_praticiens,
        "postes": stats_par_poste(debut, fin),
        "totaux": stats_totales(debut, fin),
    })


@exige_niveau(NIVEAU_ADMINISTRATEUR)
def praticiens(request):
    return render(request, "planning/praticiens.html", {
        "praticiens": Praticien.objects.select_related("user").order_by("nom"),
    })


@exige_niveau(NIVEAU_ADMINISTRATEUR)
def praticien_form(request, pk=None):
    praticien = get_object_or_404(Praticien, pk=pk) if pk else None
    form = PraticienForm(request.POST or None, instance=praticien)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Praticien enregistré.")
        return redirect("praticiens")
    return render(request, "planning/praticien_form.html", {"form": form, "praticien": praticien})


@require_POST
@exige_niveau(NIVEAU_ADMINISTRATEUR)
def praticien_supprimer(request, pk: int):
    praticien = get_object_or_404(Praticien, pk=pk)
    nom = praticien.nom
    praticien.delete()
    messages.success(request, f"Praticien {nom} supprimé.")
    return redirect("praticiens")


@exige_niveau(NIVEAU_SUPERADMINISTRATEUR)
def accreditations(request):
    praticiens = Praticien.objects.select_related("user").order_by("nom")
    if request.method == "POST":
        for p in praticiens:
            form = NiveauForm(request.POST, instance=p, prefix=f"p{p.pk}")
            if form.is_valid():
                form.save()
        messages.success(request, "Accréditations mises à jour.")
        return redirect("accreditations")
    forms = [(p, NiveauForm(instance=p, prefix=f"p{p.pk}")) for p in praticiens]
    return render(request, "planning/accreditations.html", {"forms": forms})


@login_required
def disponibilites(request):
    today = timezone.localdate()
    courant = praticien_de(request)
    if courant is None:
        raise PermissionDenied("Aucun profil praticien n'est associé à ce compte.")
    if niveau_de(request) >= 3:
        praticien_id = request.GET.get("praticien") or request.POST.get("praticien")
        if praticien_id:
            courant = get_object_or_404(Praticien, pk=praticien_id)

    annee = int(request.GET.get("annee", today.year))
    mois = int(request.GET.get("mois", today.month))
    if request.method == "POST":
        annee = int(request.POST.get("annee", annee))
        mois = int(request.POST.get("mois", mois))
        premier = dt.date(annee, mois, 1)
        dernier = dt.date(annee + (mois == 12), (mois % 12) + 1, 1) - dt.timedelta(days=1)
        courant_date = premier
        while courant_date <= dernier:
            etat = request.POST.get(f"etat_{courant_date.isoformat()}", "")
            Disponibilite.objects.filter(praticien=courant, date=courant_date).delete()
            if etat == "dispo_journee":
                Disponibilite.objects.create(praticien=courant, date=courant_date,
                                              part="journee", disponible=True)
            elif etat == "indispo_journee":
                Disponibilite.objects.create(praticien=courant, date=courant_date,
                                              part="journee", disponible=False)
            elif etat == "indispo_matin":
                Disponibilite.objects.create(praticien=courant, date=courant_date,
                                              part="matin", disponible=False)
            elif etat == "indispo_aprem":
                Disponibilite.objects.create(praticien=courant, date=courant_date,
                                              part="aprem", disponible=False)
            courant_date += dt.timedelta(days=1)
        messages.success(request, "Disponibilités enregistrées.")
        return redirect(f"/disponibilites/?annee={annee}&mois={mois}"
                        + (f"&praticien={courant.pk}" if courant != praticien_de(request) else ""))

    premier = dt.date(annee, mois, 1)
    dernier = dt.date(annee + (mois == 12), (mois % 12) + 1, 1) - dt.timedelta(days=1)
    dispo = {
        (d.date, d.part): d.disponible
        for d in Disponibilite.objects.filter(praticien=courant, date__gte=premier, date__lte=dernier)
    }
    lignes = []
    courant_date = premier
    while courant_date <= dernier:
        dispo_j = dispo.get((courant_date, "journee"))
        dispo_m = dispo.get((courant_date, "matin"))
        dispo_a = dispo.get((courant_date, "aprem"))
        if dispo_j is True:
            etat = "dispo_journee"
        elif dispo_j is False:
            etat = "indispo_journee"
        elif dispo_m is False and dispo_a is False:
            etat = "indispo_journee"
        elif dispo_m is False:
            etat = "indispo_matin"
        elif dispo_a is False:
            etat = "indispo_aprem"
        else:
            etat = ""
        lignes.append({"date": courant_date, "etat": etat, "ferie": est_ferie(courant_date)})
        courant_date += dt.timedelta(days=1)

    return render(request, "planning/disponibilites.html", {
        "praticien": courant,
        "praticiens": Praticien.objects.order_by("nom") if niveau_de(request) >= 3 else [],
        "lignes": lignes,
        "annee": annee,
        "mois": mois,
        "mois_nom": MOIS_NOMS[mois - 1],
        "mois_noms": MOIS_NOMS,
        "annees": range(today.year - 1, today.year + 2),
        "etats": [
            ("", "—"),
            ("dispo_journee", "Disponible (journée)"),
            ("indispo_journee", "Indisponible (journée)"),
            ("indispo_matin", "Indisponible (matin)"),
            ("indispo_aprem", "Indisponible (après-midi)"),
        ],
    })
