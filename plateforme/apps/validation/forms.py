from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.noyau.forms import StyleBootstrapMixin

from .models import Circuit, Decision, Delegation, EtapeCircuit


class DecisionForm(StyleBootstrapMixin, forms.Form):
    decision = forms.ChoiceField(label="Décision", choices=Decision.CHOIX)
    motif = forms.CharField(
        label="Motif",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Obligatoire pour un rejet ou un renvoi.",
    )

    def clean(self):
        donnees = super().clean()
        if donnees.get("decision") in (Decision.REJETER, Decision.RENVOYER) and not donnees.get("motif", "").strip():
            self.add_error("motif", "Le motif est obligatoire pour un rejet ou un renvoi.")
        return donnees


class AnnulationForm(StyleBootstrapMixin, forms.Form):
    motif = forms.CharField(label="Motif d'annulation", widget=forms.Textarea(attrs={"rows": 3}))


class DelegationForm(StyleBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Delegation
        fields = ["delegataire", "debut", "fin"]
        widgets = {"debut": forms.DateInput(attrs={"type": "date"}), "fin": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, delegant=None, **kwargs):
        self.delegant = delegant
        super().__init__(*args, **kwargs)
        self.fields["delegataire"].queryset = (
            get_user_model().objects.filter(is_active=True).exclude(pk=delegant.pk).select_related("agent")
        )

    def clean(self):
        donnees = super().clean()
        debut, fin = donnees.get("debut"), donnees.get("fin")
        if debut and fin and fin < debut:
            self.add_error("fin", "La date de fin doit suivre la date de début.")
        if fin and fin < timezone.localdate():
            self.add_error("fin", "La délégation doit couvrir au moins une date à venir.")
        return donnees


class CircuitForm(StyleBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Circuit
        fields = ["code", "libelle", "actif"]


class EtapeForm(StyleBootstrapMixin, forms.ModelForm):
    class Meta:
        model = EtapeCircuit
        fields = ["ordre", "libelle", "mode", "profil", "utilisateur", "seuil_montant", "actif"]
