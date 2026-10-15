"""Connexion, déconnexion, mot de passe et double authentification (TOTP)."""

import base64
from io import BytesIO

import qrcode
import qrcode.image.svg
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.journal.services import journaliser

from .forms import ChangementMotDePasseForm, CodeOTPForm, ConnexionForm


class ConnexionView(auth_views.LoginView):
    template_name = "registration/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True


class DeconnexionView(auth_views.LogoutView):
    pass


class ChangementMotDePasseView(auth_views.PasswordChangeView):
    template_name = "composants/formulaire.html"
    form_class = ChangementMotDePasseForm
    success_url = reverse_lazy("tableau_de_bord")
    extra_context = {"titre": "Changer mon mot de passe", "url_retour": reverse_lazy("tableau_de_bord")}

    def form_valid(self, form):
        reponse = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        journaliser(self.request, "droits", "Changement de son mot de passe")
        messages.success(self.request, "Mot de passe modifié.")
        return reponse


def _qr_svg(uri):
    image = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    tampon = BytesIO()
    image.save(tampon)
    return "data:image/svg+xml;base64," + base64.b64encode(tampon.getvalue()).decode()


class ActivationOTPView(LoginRequiredMixin, View):
    """Première activation : un appareil TOTP non confirmé est créé, puis
    confirmé lorsque l'utilisateur saisit un code valide."""

    template_name = "registration/otp_activation.html"

    def _appareil(self, request):
        if TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
            return None
        appareil = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if appareil is None:
            appareil = TOTPDevice.objects.create(
                user=request.user, name="Application d'authentification", confirmed=False
            )
        return appareil

    def _rendre(self, request, appareil, form):
        cle = base64.b32encode(appareil.bin_key).decode()
        return render(request, self.template_name, {"form": form, "qr": _qr_svg(appareil.config_url), "cle": cle})

    def get(self, request):
        appareil = self._appareil(request)
        if appareil is None:
            return redirect("otp_verification")
        return self._rendre(request, appareil, CodeOTPForm())

    def post(self, request):
        appareil = self._appareil(request)
        if appareil is None:
            return redirect("otp_verification")
        form = CodeOTPForm(request.POST)
        if form.is_valid() and appareil.verify_token(form.cleaned_data["code"]):
            appareil.confirmed = True
            appareil.save(update_fields=["confirmed"])
            otp_login(request, appareil)
            journaliser(request, "otp", "Activation de la double authentification")
            messages.success(request, "Double authentification activée.")
            return redirect("tableau_de_bord")
        if form.is_valid():
            form.add_error("code", "Code incorrect ou expiré. Vérifiez l'heure de votre téléphone.")
        return self._rendre(request, appareil, form)


class VerificationOTPView(LoginRequiredMixin, View):
    template_name = "registration/otp_verification.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CodeOTPForm()})

    def post(self, request):
        form = CodeOTPForm(request.POST)
        if form.is_valid():
            for appareil in TOTPDevice.objects.filter(user=request.user, confirmed=True):
                if appareil.verify_token(form.cleaned_data["code"]):
                    otp_login(request, appareil)
                    suivant = request.GET.get("next", "")
                    if not url_has_allowed_host_and_scheme(suivant, {request.get_host()}, request.is_secure()):
                        suivant = "tableau_de_bord"
                    return redirect(suivant)
            form.add_error("code", "Code incorrect ou expiré.")
            journaliser(request, "otp_echec", "Code de double authentification refusé")
        return render(request, self.template_name, {"form": form})
