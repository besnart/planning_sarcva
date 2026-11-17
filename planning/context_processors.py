from .permissions import niveau_de, praticien_de


def navigation(request):
    return {
        "niveau": niveau_de(request),
        "praticien_courant": praticien_de(request),
    }
