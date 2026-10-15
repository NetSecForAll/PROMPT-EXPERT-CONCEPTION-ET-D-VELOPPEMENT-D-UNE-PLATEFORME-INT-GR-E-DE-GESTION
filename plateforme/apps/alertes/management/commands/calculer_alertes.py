from django.core.management.base import BaseCommand

from apps.alertes.registre import calculer_alertes


class Command(BaseCommand):
    help = "Calcule toutes les règles d'alerte (exécutée chaque nuit par la tâche planifiée)."

    def handle(self, *args, **options):
        for code, resultat in calculer_alertes().items():
            self.stdout.write(f"{code} : {resultat}")
