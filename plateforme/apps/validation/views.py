from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from apps.noyau import services as services_noyau
from apps.noyau.vues_generiques import CreationView, Filtre, ListeView, ModificationView

from . import services
from .forms import AnnulationForm, CircuitForm, DecisionForm, DelegationForm, EtapeForm
from .models import Circuit, Delegation, EtapeCircuit, InstanceValidation


class AValiderView(LoginRequiredMixin, TemplateView):
    template_name = "validation/a_valider.html"

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["instances"] = services.instances_a_valider(self.request.user)
        contexte["mes_demandes"] = InstanceValidation.objects.filter(demandeur=self.request.user).select_related(
            "circuit", "etape_courante", "content_type"
        )[:50]
        return contexte


class DetailView(LoginRequiredMixin, View):
    template_name = "validation/detail.html"

    def _contexte(self, request, instance, form=None, form_annulation=None):
        peut, delegant = services.peut_decider(request.user, instance)
        return {
            "instance": instance,
            "decisions": instance.decisions.select_related("valideur__agent", "etape", "par_delegation_de"),
            "peut_decider": peut,
            "delegant": delegant,
            "form": form or DecisionForm(),
            "peut_annuler": instance.statut == InstanceValidation.EN_COURS and request.user.pk == instance.demandeur_id,
            "form_annulation": form_annulation or AnnulationForm(),
            "valideurs": services.valideurs_effectifs(instance)
            if instance.statut == InstanceValidation.EN_COURS
            else [],
        }

    def _instance(self, request, pk):
        instance = get_object_or_404(
            InstanceValidation.objects.select_related("circuit", "etape_courante", "demandeur__agent"),
            pk=pk,
        )
        if not services.peut_consulter(request.user, instance):
            raise PermissionDenied
        return instance

    def get(self, request, pk):
        instance = self._instance(request, pk)
        return render(request, self.template_name, self._contexte(request, instance))

    def post(self, request, pk):
        instance = self._instance(request, pk)
        if "annuler" in request.POST:
            form_annulation = AnnulationForm(request.POST)
            if form_annulation.is_valid():
                try:
                    services.annuler(instance, request.user, form_annulation.cleaned_data["motif"], request=request)
                except ValidationError as erreur:
                    messages.error(request, " ".join(erreur.messages))
                else:
                    messages.success(request, "Demande annulée.")
                return redirect(instance.get_absolute_url())
            return render(
                request, self.template_name, self._contexte(request, instance, form_annulation=form_annulation)
            )

        form = DecisionForm(request.POST)
        if form.is_valid():
            try:
                services.decider(
                    instance,
                    request.user,
                    form.cleaned_data["decision"],
                    form.cleaned_data["motif"],
                    request=request,
                )
            except ValidationError as erreur:
                form.add_error(None, erreur)
            else:
                messages.success(request, "Décision enregistrée.")
                return redirect("validation:a_valider")
        return render(request, self.template_name, self._contexte(request, instance, form=form))


class DelegationsView(LoginRequiredMixin, View):
    template_name = "validation/delegations.html"

    def _rendre(self, request, form):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "donnees": Delegation.objects.filter(delegant=request.user).select_related("delegataire"),
                "recues": Delegation.objects.filter(delegataire=request.user, actif=True).select_related("delegant"),
            },
        )

    def get(self, request):
        return self._rendre(request, DelegationForm(delegant=request.user))

    def post(self, request):
        if "terminer" in request.POST:
            delegation = get_object_or_404(Delegation, pk=request.POST["terminer"], delegant=request.user)
            services_noyau.desactiver(delegation, request.user)
            messages.success(request, "Délégation terminée.")
            return redirect("validation:delegations")
        form = DelegationForm(request.POST, delegant=request.user)
        if form.is_valid():
            delegation = form.save(commit=False)
            delegation.delegant = request.user
            try:
                services_noyau.enregistrer(delegation, request.user)
            except ValidationError as erreur:
                form.add_error(None, erreur)
            else:
                messages.success(request, "Délégation enregistrée.")
                return redirect("validation:delegations")
        return self._rendre(request, form)


class CircuitListeView(ListeView):
    model = Circuit
    permission_required = "validation.view_circuit"
    titre = "Circuits de validation"
    colonnes = [
        ("code", "Code", "code"),
        ("libelle", "Libellé", "libelle"),
        (lambda c: c.etapes.filter(actif=True).count(), "Étapes actives", None),
        ("actif", "Actif", "actif"),
    ]
    champs_recherche = ["code", "libelle"]
    url_creation = reverse_lazy("validation:circuit_creer")
    permission_creation = "validation.add_circuit"


class CircuitCreationView(CreationView):
    model = Circuit
    form_class = CircuitForm
    permission_required = "validation.add_circuit"
    titre = "Nouveau circuit"

    def redirection(self):
        return redirect("validation:circuit_modifier", self.object.pk)


class CircuitModificationView(ModificationView):
    model = Circuit
    form_class = CircuitForm
    permission_required = "validation.change_circuit"
    titre = "Circuit de validation"
    template_name = "validation/circuit.html"
    url_retour = reverse_lazy("validation:circuits")

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["etapes"] = self.object.etapes.select_related("profil", "utilisateur")
        return contexte


class EtapeCreationView(CreationView):
    model = EtapeCircuit
    form_class = EtapeForm
    permission_required = "validation.add_etapecircuit"
    titre = "Nouvelle étape"

    def dispatch(self, request, *args, **kwargs):
        self.circuit = get_object_or_404(Circuit, pk=kwargs["circuit"])
        self.url_retour = reverse("validation:circuit_modifier", args=[self.circuit.pk])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.circuit = self.circuit
        return form


class EtapeModificationView(ModificationView):
    model = EtapeCircuit
    form_class = EtapeForm
    permission_required = "validation.change_etapecircuit"
    titre = "Modifier l'étape"

    def get_success_url(self):
        return reverse("validation:circuit_modifier", args=[self.object.circuit_id])

    def get_context_data(self, **kwargs):
        self.url_retour = reverse("validation:circuit_modifier", args=[self.object.circuit_id])
        return super().get_context_data(**kwargs)

    def redirection(self):
        return redirect("validation:circuit_modifier", self.object.circuit_id)


class HistoriqueValidationsView(ListeView):
    model = InstanceValidation
    permission_required = "validation.view_instancevalidation"
    titre = "Toutes les validations"
    template_name = "composants/liste.html"
    colonnes = [
        ("soumise_le", "Soumise le", "soumise_le"),
        ("circuit", "Circuit", None),
        ("objet", "Objet", None),
        ("demandeur", "Demandeur", None),
        ("statut", "Statut", "statut"),
        ("terminee_le", "Terminée le", "terminee_le"),
    ]
    filtres = [Filtre("statut", "Statut", InstanceValidation.STATUTS)]
    tri_defaut = "-soumise_le"
    permission_ouverture = "validation.view_instancevalidation"

    def get_base_queryset(self):
        return InstanceValidation.objects.select_related("circuit", "demandeur__agent", "content_type")
