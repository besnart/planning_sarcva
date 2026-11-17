from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from planning import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="planning/login.html"),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.planning_annee_mois_courant, name="planning_annee_mois_courant"),
    path("planning/<int:annee>/<int:mois>/", views.planning_mois, name="planning_mois"),
    path("planning/<int:annee>/<int:mois>/modifier/", views.modifier_poste, name="modifier_poste"),
    path("planning/<int:annee>/<int:mois>/fermeture/", views.basculer_fermeture, name="basculer_fermeture"),
    path("planning/<int:annee>/<int:mois>/etiquette/", views.modifier_etiquette, name="modifier_etiquette"),
    path("planning/<int:annee>/<int:mois>/generer/", views.generer_quadrimestre, name="generer_quadrimestre"),
    path("stats/", views.stats, name="stats"),
    path("praticiens/", views.praticiens, name="praticiens"),
    path("praticiens/nouveau/", views.praticien_form, name="praticien_nouveau"),
    path("praticiens/<int:pk>/", views.praticien_form, name="praticien_modifier"),
    path("praticiens/<int:pk>/supprimer/", views.praticien_supprimer, name="praticien_supprimer"),
    path("accreditations/", views.accreditations, name="accreditations"),
    path("disponibilites/", views.disponibilites, name="disponibilites"),
]
