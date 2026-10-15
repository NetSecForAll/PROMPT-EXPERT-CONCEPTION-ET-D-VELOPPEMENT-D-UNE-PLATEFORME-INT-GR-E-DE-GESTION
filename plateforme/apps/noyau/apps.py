from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate


def _apres_migration(sender, **kwargs):
    # Les permissions de toutes les applications doivent exister avant
    # d'être attribuées aux profils.
    from django.contrib.auth.management import create_permissions

    from .profils import synchroniser_profils

    for config in apps.get_app_configs():
        create_permissions(config, verbosity=0)
    synchroniser_profils()


class NoyauConfig(AppConfig):
    name = "apps.noyau"
    label = "noyau"
    verbose_name = "Noyau"

    def ready(self):
        from auditlog.registry import auditlog

        from . import models

        post_migrate.connect(_apres_migration, sender=self)
        for modele in (models.Site, models.Service, models.Agent, models.Parametre):
            auditlog.register(modele)
        auditlog.register(
            models.Utilisateur,
            exclude_fields=["password", "last_login"],
            m2m_fields={"groups"},
        )
