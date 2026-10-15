from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView

from .models import Alerte
from .services import alertes_actives, prendre_en_compte


class MesAlertesView(LoginRequiredMixin, ListView):
    template_name = "alertes/liste.html"
    context_object_name = "alertes"
    paginate_by = 25

    def get_queryset(self):
        alertes = alertes_actives(self.request.user)
        gravite = self.request.GET.get("gravite")
        if gravite in {str(g) for g, _ in Alerte.GRAVITES}:
            alertes = alertes.filter(gravite=gravite)
        return alertes

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte.update(gravites=Alerte.GRAVITES, gravite=self.request.GET.get("gravite", ""))
        return contexte


class PriseEnCompteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        alerte = get_object_or_404(Alerte, pk=pk, destinataire=request.user, active=True)
        prendre_en_compte(alerte)
        messages.success(request, "Alerte prise en compte.")
        suivant = request.POST.get("suivant", "")
        if (
            alerte.lien
            and request.POST.get("ouvrir")
            and url_has_allowed_host_and_scheme(alerte.lien, {request.get_host()})
        ):
            return redirect(alerte.lien)
        if url_has_allowed_host_and_scheme(suivant, {request.get_host()}):
            return redirect(suivant or "alertes:liste")
        return redirect("alertes:liste")
