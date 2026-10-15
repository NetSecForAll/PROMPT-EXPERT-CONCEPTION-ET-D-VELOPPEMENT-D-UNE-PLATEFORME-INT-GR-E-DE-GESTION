from django.shortcuts import redirect
from django.urls import reverse

from .permissions import doit_utiliser_double_authentification

CHEMINS_LIBRES = ("/static/",)
VUES_LIBRES = ("otp_activation", "otp_verification", "deconnexion", "connexion")


class DoubleAuthentificationMiddleware:
    """Impose la double authentification (TOTP) aux profils d'administration.

    Tant que l'utilisateur concerné n'a pas validé un code, il ne peut ouvrir
    que les pages d'activation ou de vérification, ou se déconnecter.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utilisateur = request.user
        if (
            utilisateur.is_authenticated
            and not utilisateur.is_verified()
            and doit_utiliser_double_authentification(utilisateur)
            and not request.path.startswith(CHEMINS_LIBRES)
            and request.path not in {reverse(v) for v in VUES_LIBRES}
        ):
            from django_otp.plugins.otp_totp.models import TOTPDevice

            if TOTPDevice.objects.filter(user=utilisateur, confirmed=True).exists():
                return redirect("otp_verification")
            return redirect("otp_activation")
        return self.get_response(request)


class EnTetesSecuriteMiddleware:
    """Politique de sécurité du contenu : aucun script externe ni en ligne."""

    CSP = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reponse = self.get_response(request)
        reponse.setdefault("Content-Security-Policy", self.CSP)
        reponse.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return reponse
