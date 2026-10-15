from axes.signals import user_locked_out
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .services import journaliser


@receiver(user_logged_in)
def connexion(sender, request, user, **kwargs):
    journaliser(request, "connexion", "Connexion réussie", utilisateur=user)


@receiver(user_logged_out)
def deconnexion(sender, request, user, **kwargs):
    if user is not None:
        journaliser(request, "deconnexion", "Déconnexion", utilisateur=user)


@receiver(user_login_failed)
def echec_connexion(sender, credentials, request=None, **kwargs):
    journaliser(
        request,
        "connexion_echec",
        "Identifiant ou mot de passe incorrect",
        identifiant_saisi=str(credentials.get("username", "")),
    )


@receiver(user_locked_out)
def verrouillage(sender, request, username=None, ip_address=None, **kwargs):
    journaliser(
        request,
        "verrouillage",
        "Compte verrouillé 15 minutes après 5 échecs",
        identifiant_saisi=str(username or ""),
    )
