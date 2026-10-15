from django.apps import AppConfig


class JournalConfig(AppConfig):
    name = "apps.journal"
    label = "journal"
    verbose_name = "Journal"

    def ready(self):
        from . import signaux  # noqa: F401
