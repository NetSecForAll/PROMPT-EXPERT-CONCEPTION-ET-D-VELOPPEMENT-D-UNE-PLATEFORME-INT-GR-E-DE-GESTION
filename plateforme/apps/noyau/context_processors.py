from django.conf import settings

from .profils import libelle


def plateforme(request):
    contexte = {"environnement": settings.ENVIRONNEMENT, "en_production": settings.EN_PRODUCTION}
    utilisateur = getattr(request, "user", None)
    if utilisateur is not None and utilisateur.is_authenticated:
        from apps.alertes.services import alertes_actives
        from apps.validation.services import instances_a_valider

        contexte.update(
            profils_utilisateur=sorted(libelle(c) for c in utilisateur.codes_profils),
            nb_alertes=alertes_actives(utilisateur).filter(prise_en_compte_le__isnull=True).count(),
            nb_validations=len(instances_a_valider(utilisateur)),
        )
    return contexte
