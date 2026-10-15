from django.apps import AppConfig


class ValidationConfig(AppConfig):
    name = "apps.validation"
    label = "validation"
    verbose_name = "Validation"

    def ready(self):
        from auditlog.registry import auditlog

        from . import models

        for modele in (models.Circuit, models.EtapeCircuit, models.Delegation):
            auditlog.register(modele)
