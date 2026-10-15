from django.apps import AppConfig


class AlertesConfig(AppConfig):
    name = "apps.alertes"
    label = "alertes"
    verbose_name = "Alertes"

    def ready(self):
        from . import regles  # noqa: F401  (enregistre les règles du socle)
