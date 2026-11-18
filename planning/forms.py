from django import forms
from django.contrib.auth.models import User

from .models import NIVEAUX, Praticien


class PraticienForm(forms.ModelForm):
    class Meta:
        model = Praticien
        fields = ["nom", "user", "quote_part", "type", "dj"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "user": forms.Select(attrs={"class": "form-select"}),
            "quote_part": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "type": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].required = False
        self.fields["user"].queryset = User.objects.order_by("username")
        self.fields["user"].empty_label = "— aucun compte —"


class NiveauForm(forms.ModelForm):
    class Meta:
        model = Praticien
        fields = ["niveau"]
        widgets = {"niveau": forms.Select(attrs={"class": "form-select form-select-sm"})}


class DisponibiliteLigneForm(forms.Form):
    """Une ligne du formulaire de disponibilites : une date, un etat."""

    ETATS = [
        ("", "—"),
        ("dispo_journee", "Disponible (journée)"),
        ("indispo_journee", "Indisponible (journée)"),
        ("indispo_matin", "Indisponible (matin)"),
        ("indispo_aprem", "Indisponible (après-midi)"),
    ]

    def __init__(self, *args, date=None, etat="", **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"] = forms.DateField(
            initial=date, widget=forms.HiddenInput()
        )
        self.fields["etat"] = forms.ChoiceField(
            choices=self.ETATS, initial=etat, required=False,
            widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        )
