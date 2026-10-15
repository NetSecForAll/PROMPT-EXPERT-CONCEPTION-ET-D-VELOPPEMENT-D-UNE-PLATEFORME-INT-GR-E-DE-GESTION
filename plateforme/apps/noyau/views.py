from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.alertes.services import alertes_actives
from apps.journal.services import journaliser
from apps.validation.services import instances_a_valider

from .forms import (
    AgentForm,
    ParametreForm,
    ReinitialisationMotDePasseForm,
    ServiceForm,
    SiteForm,
    UtilisateurCreationForm,
    UtilisateurModificationForm,
)
from .models import Agent, Parametre, Service, Site, Utilisateur
from .permissions import PermissionRequiseMixin
from .profils import LIBELLES, libelle
from .vues_generiques import FILTRE_ACTIF, CreationView, Filtre, ListeView, ModificationView


class TableauDeBordView(LoginRequiredMixin, TemplateView):
    """Tableau de bord du socle. Les modules métier y ajouteront leurs
    indicateurs ; il n'affiche que des données réellement enregistrées."""

    template_name = "noyau/tableau_de_bord.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        utilisateur = self.request.user
        contexte["validations"] = instances_a_valider(utilisateur)[:10]
        contexte["alertes"] = alertes_actives(utilisateur).order_by("-gravite", "-cree_le")[:10]
        if utilisateur.has_perm("noyau.view_agent"):
            contexte["referentiels"] = {
                "Sites": Site.objects.filter(actif=True).count(),
                "Services": Service.objects.filter(actif=True).count(),
                "Agents": Agent.objects.filter(actif=True).count(),
            }
        return contexte


def page_introuvable(request, exception):
    return render(request, "404.html", status=404)


# --- Sites ------------------------------------------------------------------


class SiteListeView(ListeView):
    model = Site
    permission_required = "noyau.view_site"
    titre = "Sites"
    colonnes = [
        ("code", "Code", "code"),
        ("nom", "Nom", "nom"),
        ("adresse", "Adresse", None),
        ("actif", "Actif", "actif"),
    ]
    champs_recherche = ["code", "nom", "adresse"]
    filtres = [FILTRE_ACTIF]
    url_creation = reverse_lazy("noyau:site_creer")
    permission_creation = "noyau.add_site"


class SiteCreationView(CreationView):
    model = Site
    form_class = SiteForm
    permission_required = "noyau.add_site"
    titre = "Nouveau site"
    url_retour = reverse_lazy("noyau:sites")


class SiteModificationView(ModificationView):
    model = Site
    form_class = SiteForm
    permission_required = "noyau.change_site"
    titre = "Modifier le site"
    url_retour = reverse_lazy("noyau:sites")


# --- Services ---------------------------------------------------------------


class ServiceListeView(ListeView):
    model = Service
    permission_required = "noyau.view_service"
    titre = "Services"
    colonnes = [
        ("code", "Code", "code"),
        ("nom", "Nom", "nom"),
        ("site.nom", "Site", "site__nom"),
        ("parent.code", "Service parent", None),
        ("chef", "Chef de service", None),
        ("actif", "Actif", "actif"),
    ]
    champs_recherche = ["code", "nom"]
    filtres = [
        Filtre("site", "Site", lambda: [(s.pk, s.nom) for s in Site.objects.filter(actif=True)], "site_id"),
        FILTRE_ACTIF,
    ]
    url_creation = reverse_lazy("noyau:service_creer")
    permission_creation = "noyau.add_service"

    def get_base_queryset(self):
        return Service.objects.select_related("site", "parent", "chef")


class ServiceCreationView(CreationView):
    model = Service
    form_class = ServiceForm
    permission_required = "noyau.add_service"
    titre = "Nouveau service"
    url_retour = reverse_lazy("noyau:services")


class ServiceModificationView(ModificationView):
    model = Service
    form_class = ServiceForm
    permission_required = "noyau.change_service"
    titre = "Modifier le service"
    url_retour = reverse_lazy("noyau:services")


# --- Agents -----------------------------------------------------------------


class AgentListeView(ListeView):
    model = Agent
    permission_required = "noyau.view_agent"
    titre = "Agents"
    colonnes = [
        ("matricule", "Matricule", "matricule"),
        ("nom", "Nom", "nom"),
        ("prenom", "Prénom", "prenom"),
        ("fonction", "Fonction", None),
        ("service.code", "Service", "service__code"),
        ("telephone", "Téléphone", None),
        ("actif", "Actif", "actif"),
    ]
    champs_recherche = ["matricule", "nom", "prenom", "fonction"]
    filtres = [
        Filtre(
            "service", "Service", lambda: [(s.pk, s.code) for s in Service.objects.filter(actif=True)], "service_id"
        ),
        FILTRE_ACTIF,
    ]
    url_creation = reverse_lazy("noyau:agent_creer")
    permission_creation = "noyau.add_agent"

    def get_base_queryset(self):
        return Agent.objects.select_related("service")


class AgentCreationView(CreationView):
    model = Agent
    form_class = AgentForm
    permission_required = "noyau.add_agent"
    titre = "Nouvel agent"
    url_retour = reverse_lazy("noyau:agents")


class AgentModificationView(ModificationView):
    model = Agent
    form_class = AgentForm
    permission_required = "noyau.change_agent"
    titre = "Modifier l'agent"
    url_retour = reverse_lazy("noyau:agents")


# --- Paramètres -------------------------------------------------------------


class ParametreListeView(ListeView):
    model = Parametre
    permission_required = "noyau.view_parametre"
    titre = "Paramètres"
    colonnes = [("cle", "Clé", "cle"), ("valeur", "Valeur", None), ("description", "Description", None)]
    champs_recherche = ["cle", "description"]


class ParametreModificationView(ModificationView):
    model = Parametre
    form_class = ParametreForm
    permission_required = "noyau.change_parametre"
    titre = "Modifier le paramètre"
    url_retour = reverse_lazy("noyau:parametres")


# --- Comptes utilisateurs ---------------------------------------------------


def _profils(utilisateur):
    return ", ".join(sorted(libelle(c) for c in utilisateur.groups.values_list("name", flat=True)))


class UtilisateurListeView(ListeView):
    model = Utilisateur
    permission_required = "noyau.view_utilisateur"
    titre = "Comptes utilisateurs"
    colonnes = [
        ("username", "Identifiant", "username"),
        ("agent", "Agent", None),
        ("agent.service.code", "Service", None),
        (_profils, "Profils", None),
        ("is_active", "Actif", "is_active"),
        ("last_login", "Dernière connexion", "last_login"),
    ]
    champs_recherche = ["username", "agent__nom", "agent__prenom", "agent__matricule"]
    filtres = [
        Filtre("profil", "Profil", list(LIBELLES.items()), "groups__name"),
        Filtre("is_active", "Statut", [("oui", "Actifs"), ("non", "Désactivés")]),
    ]
    url_creation = reverse_lazy("noyau:utilisateur_creer")
    permission_creation = "noyau.add_utilisateur"

    def get_base_queryset(self):
        return Utilisateur.objects.select_related("agent__service").prefetch_related("groups").distinct()


class UtilisateurFormMixin:
    template_name = "composants/formulaire.html"
    url_retour = reverse_lazy("noyau:utilisateurs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["auteur"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte.update(titre=self.titre, url_retour=self.url_retour)
        return contexte

    @transaction.atomic
    def form_valid(self, form):
        anciens = set(form.instance.groups.values_list("name", flat=True)) if form.instance.pk else set()
        self.object = form.save()
        nouveaux = set(self.object.groups.values_list("name", flat=True))
        if anciens != nouveaux:
            journaliser(
                self.request,
                "droits",
                f"Profils de {self.object.username} : {sorted(anciens)} -> {sorted(nouveaux)}",
                objet=self.object,
            )
        messages.success(self.request, "Compte enregistré.")
        return redirect(self.url_retour)


class UtilisateurCreationView(PermissionRequiseMixin, UtilisateurFormMixin, CreateView):
    model = Utilisateur
    form_class = UtilisateurCreationForm
    permission_required = "noyau.add_utilisateur"
    titre = "Nouveau compte"


class UtilisateurModificationView(PermissionRequiseMixin, UtilisateurFormMixin, UpdateView):
    model = Utilisateur
    form_class = UtilisateurModificationForm
    permission_required = "noyau.change_utilisateur"
    titre = "Modifier le compte"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["actions_secondaires"] = [
            ("Réinitialiser le mot de passe", reverse_lazy("noyau:utilisateur_mdp", args=[self.object.pk])),
        ]
        return contexte


class ReinitialisationMotDePasseView(PermissionRequiseMixin, View):
    permission_required = "noyau.change_utilisateur"
    template_name = "composants/formulaire.html"

    def _contexte(self, cible, form):
        return {
            "form": form,
            "titre": f"Nouveau mot de passe pour {cible.username}",
            "url_retour": reverse_lazy("noyau:utilisateur_modifier", args=[cible.pk]),
            "confirmation": "Le mot de passe actuel de ce compte cessera de fonctionner. Continuer ?",
        }

    def get(self, request, pk):
        cible = get_object_or_404(Utilisateur, pk=pk)
        return render(
            request, self.template_name, self._contexte(cible, ReinitialisationMotDePasseForm(utilisateur=cible))
        )

    def post(self, request, pk):
        cible = get_object_or_404(Utilisateur, pk=pk)
        form = ReinitialisationMotDePasseForm(request.POST, utilisateur=cible)
        if not form.is_valid():
            return render(request, self.template_name, self._contexte(cible, form))
        cible.set_password(form.cleaned_data["mot_de_passe1"])
        cible.save(update_fields=["password"])
        journaliser(request, "droits", f"Mot de passe réinitialisé pour {cible.username}", objet=cible)
        messages.success(request, "Mot de passe réinitialisé. Communiquez-le à l'utilisateur par un canal sûr.")
        return redirect("noyau:utilisateurs")


class ProfilListeView(ListeView):
    """Consultation des profils et de leurs permissions."""

    model = Group
    permission_required = "noyau.view_utilisateur"
    titre = "Profils"
    colonnes = [
        (lambda g: libelle(g.name), "Profil", None),
        (lambda g: g.user_set.filter(is_active=True).count(), "Comptes actifs", None),
        (lambda g: g.permissions.count(), "Permissions", None),
    ]

    def get_base_queryset(self):
        return Group.objects.filter(name__in=LIBELLES.keys()).order_by("name")
