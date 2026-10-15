from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import Alerte


def alertes_actives(utilisateur):
    return Alerte.objects.filter(destinataire=utilisateur, active=True)


@transaction.atomic
def lever(cle, destinataires, titre, code_regle, message="", gravite=Alerte.ATTENTION, lien="", objet=None):
    """Crée l'alerte pour chaque destinataire, sans doublon : si une alerte
    active de même clé existe déjà, son texte est mis à jour."""
    alertes = []
    for destinataire in {d for d in destinataires if d is not None and d.is_active}:
        alerte, creee = Alerte.objects.get_or_create(
            cle=cle,
            destinataire=destinataire,
            active=True,
            defaults={
                "titre": titre,
                "message": message,
                "gravite": gravite,
                "code_regle": code_regle,
                "lien": lien,
                "content_type": ContentType.objects.get_for_model(objet) if objet is not None else None,
                "object_id": objet.pk if objet is not None else None,
            },
        )
        if not creee and (alerte.titre, alerte.message, alerte.gravite) != (titre, message, gravite):
            alerte.titre, alerte.message, alerte.gravite = titre, message, gravite
            alerte.save(update_fields=["titre", "message", "gravite"])
        alertes.append(alerte)
    return alertes


def resoudre(cle, destinataires=None):
    alertes = Alerte.objects.filter(cle=cle, active=True)
    if destinataires is not None:
        alertes = alertes.filter(destinataire__in=list(destinataires))
    return alertes.update(active=False, resolue_le=timezone.now())


def prendre_en_compte(alerte):
    alerte.prise_en_compte_le = timezone.now()
    champs = ["prise_en_compte_le"]
    if alerte.gravite == Alerte.INFO:
        alerte.active = False
        alerte.resolue_le = alerte.prise_en_compte_le
        champs += ["active", "resolue_le"]
    alerte.save(update_fields=champs)
