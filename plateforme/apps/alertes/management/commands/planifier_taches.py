from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule


class Command(BaseCommand):
    help = "Crée ou met à jour les tâches planifiées (idempotent)."

    def handle(self, *args, **options):
        demain = timezone.localdate() + timedelta(days=1)
        prochaine = timezone.make_aware(datetime.combine(demain, time(2, 0)))
        _, cree = Schedule.objects.update_or_create(
            name="Calcul des alertes",
            defaults={
                "func": "apps.alertes.taches.calculer_alertes",
                "schedule_type": Schedule.DAILY,
                "next_run": prochaine,
                "repeats": -1,
            },
        )
        self.stdout.write(("Créée" if cree else "Mise à jour") + " : Calcul des alertes, chaque jour à 02:00")
