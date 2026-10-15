from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class PermissionRequiseMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Vue réservée aux utilisateurs connectés disposant de la permission.

    Un utilisateur connecté sans le droit reçoit une page 403 (journalisée par
    ``apps.journal.views.acces_refuse``) ; un visiteur anonyme est redirigé
    vers la page de connexion.
    """


PROFILS_ADMINISTRATION = ("admin_technique", "admin_fonctionnel")


def doit_utiliser_double_authentification(utilisateur):
    return utilisateur.is_superuser or utilisateur.a_profil(*settings.PROFILS_DOUBLE_AUTHENTIFICATION)


def peut_attribuer_profil(utilisateur, code_profil):
    """Seuls l'administrateur technique et le superutilisateur attribuent les
    profils d'administration ; cela évite qu'un administrateur fonctionnel
    s'octroie ou octroie des droits techniques."""
    if code_profil in PROFILS_ADMINISTRATION:
        return utilisateur.is_superuser or utilisateur.a_profil("admin_technique")
    return True
