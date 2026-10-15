import pytest
from auditlog.models import LogEntry
from django.db import DatabaseError, transaction

from apps.journal.models import EvenementSecurite
from apps.noyau import services


@pytest.fixture
def evenement(db):
    return EvenementSecurite.objects.create(type="connexion", description="test")


def test_evenement_non_modifiable(evenement):
    with pytest.raises(DatabaseError, match="ne peut être ni modifié ni supprimé"), transaction.atomic():
        EvenementSecurite.objects.filter(pk=evenement.pk).update(description="falsifié")


def test_evenement_non_supprimable(evenement):
    with pytest.raises(DatabaseError), transaction.atomic():
        EvenementSecurite.objects.filter(pk=evenement.pk).delete()
    assert EvenementSecurite.objects.filter(pk=evenement.pk).exists()


def test_historique_avant_apres(organisation, equipe):
    service = organisation["logistique"]
    service.nom = "Logistique et moyens généraux"
    services.enregistrer(service, equipe["admin_fonc"])
    entree = LogEntry.objects.get_for_object(service).filter(action=LogEntry.Action.UPDATE).latest("timestamp")
    assert entree.changes_dict["nom"] == ["Logistique", "Logistique et moyens généraux"]
    with pytest.raises(DatabaseError), transaction.atomic():
        LogEntry.objects.filter(pk=entree.pk).delete()


def test_historique_consultable_par_auditeur(equipe, connecter):
    assert connecter(equipe["auditeur"]).get("/journal/modifications/").status_code == 200
