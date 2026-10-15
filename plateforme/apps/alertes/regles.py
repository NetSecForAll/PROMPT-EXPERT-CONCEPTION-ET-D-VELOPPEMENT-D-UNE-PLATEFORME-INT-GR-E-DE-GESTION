"""Règles d'alerte du socle."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Alerte
from .registre import regle
from .services import lever


@regle("validation_en_retard")
def validations_en_retard():
    """Signale aux valideurs les demandes bloquées à la même étape depuis plus
    de ALERTE_VALIDATION_EN_ATTENTE_JOURS jours ; résout les signalements
    devenus sans objet."""
    from apps.validation.models import InstanceValidation
    from apps.validation.services import valideurs_effectifs

    limite = timezone.now() - timedelta(days=settings.ALERTE_VALIDATION_EN_ATTENTE_JOURS)
    en_retard = InstanceValidation.objects.filter(
        statut=InstanceValidation.EN_COURS,
        etape_depuis__lt=limite,
    ).select_related("circuit", "etape_courante", "demandeur")
    cles = set()
    for instance in en_retard:
        cle = f"validation_retard:{instance.pk}:{instance.etape_courante_id}"
        cles.add(cle)
        jours = (timezone.now() - instance.etape_depuis).days
        lever(
            cle,
            valideurs_effectifs(instance),
            titre=f"En attente depuis {jours} jours : {instance.objet}",
            message=f"{instance.circuit} — étape « {instance.etape_courante.libelle} ».",
            code_regle="validation_en_retard",
            gravite=Alerte.CRITIQUE,
            lien=instance.get_absolute_url(),
            objet=instance,
        )
    obsoletes = Alerte.objects.filter(code_regle="validation_en_retard", active=True).exclude(cle__in=cles)
    resolues = obsoletes.update(active=False, resolue_le=timezone.now())
    return {"levees": len(cles), "resolues": resolues}
