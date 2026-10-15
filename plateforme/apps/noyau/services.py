"""Règles de gestion communes : enregistrement contrôlé et désactivation."""

from django.core.exceptions import ValidationError
from django.db import transaction

MESSAGE_CONFLIT = (
    "Cette fiche a été modifiée par un autre utilisateur pendant votre saisie. "
    "Rechargez la page pour voir la version à jour, puis refaites votre modification."
)


@transaction.atomic
def enregistrer(instance, utilisateur, version_attendue=None):
    """Valide puis enregistre une instance de ``ModeleBase``.

    ``version_attendue`` est la version affichée dans le formulaire : si la
    fiche a changé depuis, l'enregistrement est refusé (modification
    concurrente).
    """
    creation = instance.pk is None
    if not creation:
        version_actuelle = (
            type(instance).objects.select_for_update().values_list("version", flat=True).get(pk=instance.pk)
        )
        if version_attendue is not None and int(version_attendue) != version_actuelle:
            raise ValidationError(MESSAGE_CONFLIT)
        instance.version = version_actuelle + 1
    else:
        instance.cree_par = utilisateur
    instance.modifie_par = utilisateur
    instance.full_clean()
    instance.save()
    return instance


def desactiver(instance, utilisateur):
    instance.actif = False
    return enregistrer(instance, utilisateur)


def reactiver(instance, utilisateur):
    instance.actif = True
    return enregistrer(instance, utilisateur)
