from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone

from apps.alertes import services
from apps.alertes.models import Alerte
from apps.validation import services as validation
from apps.validation.models import InstanceValidation


def test_lever_sans_doublon(equipe):
    for _ in range(3):
        services.lever("cle:1", [equipe["agent"]], titre="Test", code_regle="test")
    assert Alerte.objects.filter(cle="cle:1", active=True).count() == 1


def test_alerte_attention_reste_active_apres_prise_en_compte(equipe):
    (alerte,) = services.lever("cle:2", [equipe["agent"]], titre="Échéance", code_regle="test")
    services.prendre_en_compte(alerte)
    alerte.refresh_from_db()
    assert alerte.active and alerte.prise_en_compte_le
    services.resoudre("cle:2")
    alerte.refresh_from_db()
    assert not alerte.active and alerte.resolue_le


def test_alerte_information_disparait_a_la_prise_en_compte(equipe):
    (alerte,) = services.lever("cle:3", [equipe["agent"]], titre="Info", code_regle="test", gravite=Alerte.INFO)
    services.prendre_en_compte(alerte)
    alerte.refresh_from_db()
    assert not alerte.active


def test_validation_en_retard(equipe, circuit, organisation):
    instance = validation.soumettre(organisation["site"], equipe["agent"], "mission")
    InstanceValidation.objects.filter(pk=instance.pk).update(etape_depuis=timezone.now() - timedelta(days=5))
    call_command("calculer_alertes")
    retard = Alerte.objects.get(code_regle="validation_en_retard", active=True)
    assert retard.destinataire == equipe["chef_prog"] and retard.gravite == Alerte.CRITIQUE
    # Une fois la demande traitée, l'alerte de retard est résolue au calcul suivant.
    validation.decider(instance, equipe["chef_prog"], "rejeter", "Trop tard")
    call_command("calculer_alertes")
    assert not Alerte.objects.filter(code_regle="validation_en_retard", active=True).exists()


def test_ecran_prise_en_compte(equipe, connecter):
    (alerte,) = services.lever("cle:4", [equipe["agent"]], titre="Visible", code_regle="test")
    client = connecter(equipe["agent"])
    assert "Visible" in client.get("/alertes/").content.decode()
    assert client.post(f"/alertes/{alerte.pk}/prise-en-compte/").status_code == 302
    alerte.refresh_from_db()
    assert alerte.prise_en_compte_le is not None


def test_on_ne_prend_pas_en_compte_l_alerte_d_un_autre(equipe, connecter):
    (alerte,) = services.lever("cle:5", [equipe["agent"]], titre="Privée", code_regle="test")
    assert connecter(equipe["agent2"]).post(f"/alertes/{alerte.pk}/prise-en-compte/").status_code == 404


def test_planification_idempotente(db):
    from django_q.models import Schedule

    call_command("planifier_taches")
    call_command("planifier_taches")
    assert Schedule.objects.filter(name="Calcul des alertes").count() == 1
