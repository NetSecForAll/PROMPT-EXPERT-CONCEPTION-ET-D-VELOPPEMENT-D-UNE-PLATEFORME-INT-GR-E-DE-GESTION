import pytest
from django.core.management import CommandError, call_command

from apps.noyau.models import Utilisateur


def test_demo_refusee_en_production(db, settings):
    settings.EN_PRODUCTION = True
    with pytest.raises(CommandError, match="interdites en production"):
        call_command("charger_demo")


def test_demo_identifiee_et_non_rechargeable(db):
    call_command("charger_demo")
    comptes = Utilisateur.objects.filter(username__startswith="demo.")
    assert comptes.count() == 10
    assert all(c.agent.matricule.startswith("DEMO-") for c in comptes)
    with pytest.raises(CommandError, match="déjà chargées"):
        call_command("charger_demo")
