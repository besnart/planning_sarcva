from django.contrib import admin

from .models import (
    Affectation,
    Disponibilite,
    EtiquetteBloc,
    Fermeture,
    JournalGeneration,
    Praticien,
)


@admin.register(Praticien)
class PraticienAdmin(admin.ModelAdmin):
    list_display = ("nom", "user", "quote_part", "type", "dj", "niveau")
    list_filter = ("type", "dj", "niveau")
    search_fields = ("nom", "user__username")


@admin.register(Affectation)
class AffectationAdmin(admin.ModelAdmin):
    list_display = ("date", "section", "code", "part", "index", "praticien")
    list_filter = ("section", "code", "date")
    search_fields = ("praticien__nom",)
    date_hierarchy = "date"


@admin.register(Disponibilite)
class DisponibiliteAdmin(admin.ModelAdmin):
    list_display = ("praticien", "date", "part", "disponible")
    list_filter = ("disponible", "part", "date")


@admin.register(Fermeture)
class FermetureAdmin(admin.ModelAdmin):
    list_display = ("date", "section")
    list_filter = ("section",)


@admin.register(EtiquetteBloc)
class EtiquetteBlocAdmin(admin.ModelAdmin):
    list_display = ("date", "code", "etiquette")
    list_filter = ("code", "etiquette")


@admin.register(JournalGeneration)
class JournalGenerationAdmin(admin.ModelAdmin):
    list_display = ("annee", "quadrimestre", "auteur", "date_creation")
    readonly_fields = ("date_creation",)
