import pytest
from django.core.exceptions import ValidationError

from apps.noyau import services
from apps.noyau.models import Agent, Service


def test_hierarchie_de_services_sans_boucle(organisation, equipe):
    direction = organisation["direction"]
    direction.parent = organisation["logistique"]  # LOG est déjà enfant de DG
    with pytest.raises(ValidationError, match="boucle"):
        services.enregistrer(direction, equipe["admin_fonc"])


def test_service_ne_peut_etre_son_propre_parent(organisation, equipe):
    service = organisation["logistique"]
    service.parent = service
    with pytest.raises(ValidationError):
        services.enregistrer(service, equipe["admin_fonc"])


def test_matricule_unique(organisation, equipe):
    with pytest.raises(ValidationError):
        services.enregistrer(
            Agent(matricule=equipe["agent"].agent.matricule, nom="X", prenom="Y", service=organisation["programmes"]),
            equipe["admin_fonc"],
        )


def test_enregistrer_trace_auteur_et_version(organisation, equipe):
    auteur = equipe["admin_fonc"]
    service = services.enregistrer(Service(code="NEW", nom="Nouveau", site=organisation["site"]), auteur)
    assert (service.cree_par, service.modifie_par, service.version) == (auteur, auteur, 1)
    service.nom = "Renommé"
    services.enregistrer(service, auteur, version_attendue=1)
    assert Service.objects.get(pk=service.pk).version == 2


def test_modification_concurrente_refusee(organisation, equipe):
    service = organisation["logistique"]
    copie_a = Service.objects.get(pk=service.pk)
    copie_b = Service.objects.get(pk=service.pk)
    copie_a.nom = "Modifié par A"
    services.enregistrer(copie_a, equipe["admin_fonc"], version_attendue=1)
    copie_b.nom = "Modifié par B"
    with pytest.raises(ValidationError, match="modifiée par un autre utilisateur"):
        services.enregistrer(copie_b, equipe["admin_fonc"], version_attendue=1)
    assert Service.objects.get(pk=service.pk).nom == "Modifié par A"


def test_desactivation_au_lieu_de_suppression(organisation, equipe):
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        organisation["programmes"].delete()  # des agents y sont rattachés
    services.desactiver(organisation["programmes"], equipe["admin_fonc"])
    assert Service.objects.get(pk=organisation["programmes"].pk).actif is False


def test_conflit_detecte_depuis_le_formulaire(organisation, equipe, connecter):
    client = connecter(equipe["admin_fonc"])
    url = f"/administration/services/{organisation['logistique'].pk}/"
    donnees = {
        "code": "LOG",
        "nom": "Logistique A",
        "site": organisation["site"].pk,
        "parent": organisation["direction"].pk,
        "actif": "on",
        "version_formulaire": "1",
    }
    assert client.post(url, donnees).status_code == 302
    donnees["nom"] = "Logistique B"
    reponse = client.post(url, donnees)
    assert reponse.status_code == 200
    assert "modifiée par un autre utilisateur" in reponse.content.decode()
    assert Service.objects.get(pk=organisation["logistique"].pk).nom == "Logistique A"
