from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import Group

from .models import Agent, Parametre, Service, Site, Utilisateur
from .permissions import peut_attribuer_profil
from .profils import LIBELLES, libelle


class StyleBootstrapMixin:
    """Applique les classes Bootstrap à tous les champs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            widget = champ.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                continue
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class ConnexionForm(StyleBootstrapMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "Identifiant ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé.",
    }


class ChangementMotDePasseForm(StyleBootstrapMixin, PasswordChangeForm):
    pass


class CodeOTPForm(StyleBootstrapMixin, forms.Form):
    code = forms.RegexField(
        label="Code à 6 chiffres",
        regex=r"^\d{6}$",
        max_length=6,
        error_messages={"invalid": "Saisissez les 6 chiffres affichés par l'application."},
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )


class SiteForm(StyleBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Site
        fields = ["code", "nom", "adresse", "actif"]


class ServiceForm(StyleBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = ["code", "nom", "site", "parent", "chef", "actif"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].queryset = Site.objects.filter(actif=True)
        parents = Service.objects.filter(actif=True)
        if self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parents
        self.fields["chef"].queryset = Agent.objects.filter(actif=True).select_related("service")


class AgentForm(StyleBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Agent
        fields = ["matricule", "nom", "prenom", "fonction", "service", "telephone", "email", "actif"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(actif=True)


class ParametreForm(StyleBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Parametre
        fields = ["valeur", "description"]


class ChoixProfilsField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return libelle(obj.name)


class UtilisateurFormMixin:
    """Règles communes aux formulaires de compte :

    - un compte est toujours rattaché à un agent actif sans autre compte ;
    - personne ne modifie ses propres profils ;
    - les profils d'administration ne sont attribués que par l'administrateur
      technique.
    """

    def __init__(self, *args, auteur=None, **kwargs):
        self.auteur = auteur
        super().__init__(*args, **kwargs)
        agents = Agent.objects.filter(actif=True, utilisateur__isnull=True)
        if self.instance.pk and self.instance.agent_id:
            agents = agents | Agent.objects.filter(pk=self.instance.agent_id)
        self.fields["agent"].queryset = agents.select_related("service")
        self.fields["agent"].required = True
        self.fields["groups"] = ChoixProfilsField(
            label="Profils",
            required=False,
            widget=forms.CheckboxSelectMultiple,
            queryset=Group.objects.filter(name__in=LIBELLES.keys()).order_by("name"),
            initial=self.instance.groups.all() if self.instance.pk else None,
        )
        if self.instance.pk and auteur is not None and self.instance.pk == auteur.pk:
            self.fields["groups"].disabled = True
            self.fields["groups"].help_text = "Vous ne pouvez pas modifier vos propres profils."

    def clean_groups(self):
        profils = self.cleaned_data["groups"]
        anciens = set(self.instance.groups.values_list("name", flat=True)) if self.instance.pk else set()
        for profil in profils:
            if profil.name not in anciens and not peut_attribuer_profil(self.auteur, profil.name):
                raise forms.ValidationError(
                    f"Seul l'administrateur technique peut attribuer le profil « {libelle(profil.name)} »."
                )
        retires = anciens - {p.name for p in profils}
        for code in retires:
            if not peut_attribuer_profil(self.auteur, code):
                raise forms.ValidationError(
                    f"Seul l'administrateur technique peut retirer le profil « {libelle(code)} »."
                )
        return profils


class UtilisateurCreationForm(UtilisateurFormMixin, StyleBootstrapMixin, forms.ModelForm):
    mot_de_passe1 = forms.CharField(label="Mot de passe initial", widget=forms.PasswordInput, strip=False)
    mot_de_passe2 = forms.CharField(label="Confirmation", widget=forms.PasswordInput, strip=False)

    class Meta:
        model = Utilisateur
        fields = ["username", "agent", "email", "groups"]
        labels = {"username": "Identifiant de connexion"}

    def clean(self):
        donnees = super().clean()
        mdp1, mdp2 = donnees.get("mot_de_passe1"), donnees.get("mot_de_passe2")
        if mdp1 and mdp2 and mdp1 != mdp2:
            self.add_error("mot_de_passe2", "Les deux mots de passe ne correspondent pas.")
        elif mdp1:
            utilisateur = Utilisateur(username=donnees.get("username"), email=donnees.get("email", ""))
            try:
                password_validation.validate_password(mdp1, utilisateur)
            except forms.ValidationError as erreur:
                self.add_error("mot_de_passe1", erreur)
        return donnees

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        utilisateur.set_password(self.cleaned_data["mot_de_passe1"])
        if utilisateur.agent_id:
            utilisateur.first_name = utilisateur.agent.prenom
            utilisateur.last_name = utilisateur.agent.nom
        if commit:
            utilisateur.save()
            self.save_m2m()
        return utilisateur


class UtilisateurModificationForm(UtilisateurFormMixin, StyleBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ["username", "agent", "email", "is_active", "groups"]
        labels = {"username": "Identifiant de connexion", "is_active": "Compte actif"}

    def clean_is_active(self):
        actif = self.cleaned_data["is_active"]
        if not actif and self.auteur is not None and self.instance.pk == self.auteur.pk:
            raise forms.ValidationError("Vous ne pouvez pas désactiver votre propre compte.")
        return actif


class ReinitialisationMotDePasseForm(StyleBootstrapMixin, forms.Form):
    mot_de_passe1 = forms.CharField(label="Nouveau mot de passe", widget=forms.PasswordInput, strip=False)
    mot_de_passe2 = forms.CharField(label="Confirmation", widget=forms.PasswordInput, strip=False)

    def __init__(self, *args, utilisateur=None, **kwargs):
        self.utilisateur = utilisateur
        super().__init__(*args, **kwargs)

    def clean(self):
        donnees = super().clean()
        mdp1, mdp2 = donnees.get("mot_de_passe1"), donnees.get("mot_de_passe2")
        if mdp1 and mdp2 and mdp1 != mdp2:
            self.add_error("mot_de_passe2", "Les deux mots de passe ne correspondent pas.")
        elif mdp1:
            try:
                password_validation.validate_password(mdp1, self.utilisateur)
            except forms.ValidationError as erreur:
                self.add_error("mot_de_passe1", erreur)
        return donnees
