"""Controle d'acces selon les niveaux d'accreditation.

Visionnage < Utilisateur < Administrateur < Super Administrateur
"""

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url

from .models import ORDRE_NIVEAUX, NIVEAU_VISIONNAGE, Praticien


def praticien_de(request):
    if not request.user.is_authenticated:
        return None
    return Praticien.objects.filter(user=request.user).first()


def niveau_de(request) -> int:
    """Niveau numerique : 0 = anonyme, 1 = visionnage, ... 4 = super admin."""
    if not request.user.is_authenticated:
        return 0
    p = praticien_de(request)
    if p is None:
        return ORDRE_NIVEAUX[NIVEAU_VISIONNAGE]
    return ORDRE_NIVEAUX[p.niveau]


def exige_niveau(niveau: str):
    """Decorateur : exige un niveau d'accreditation minimum (connexion requise)."""

    def decorateur(vue):
        @wraps(vue)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and niveau_de(request) >= ORDRE_NIVEAUX[niveau]:
                return vue(request, *args, **kwargs)
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), resolve_url(settings.LOGIN_URL))
            raise PermissionDenied

        return wrapper

    return decorateur


def planning_lecture(request) -> bool:
    """Le planning est lisible de partout (anonyme) si PLANNING_PUBLIC_READ, sinon Visionnage+."""
    if settings.PLANNING_PUBLIC_READ:
        return True
    return request.user.is_authenticated and niveau_de(request) >= ORDRE_NIVEAUX[NIVEAU_VISIONNAGE]
