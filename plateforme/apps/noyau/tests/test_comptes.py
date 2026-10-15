from django.contrib.auth.models import Group

from apps.journal.models import EvenementSecurite
from apps.noyau.models import Agent, Utilisateur


def _creer_agent(organisation, matricule="N001"):
    return Agent.objects.create(matricule=matricule, nom="Nouveau", prenom="Agent", service=organisation["programmes"])


def test_creation_de_compte_avec_profil(equipe, connecter, organisation):
    agent = _creer_agent(organisation)
    reponse = connecter(equipe["admin_fonc"]).post(
        "/administration/comptes/nouveau/",
        {
            "username": "nouveau",
            "agent": agent.pk,
            "email": "",
            "groups": [Group.objects.get(name="gestionnaire_stock").pk],
            "mot_de_passe1": "Un-Mot-De-Passe-Solide-42",
            "mot_de_passe2": "Un-Mot-De-Passe-Solide-42",
        },
    )
    assert reponse.status_code == 302
    compte = Utilisateur.objects.get(username="nouveau")
    assert compte.agent == agent and compte.a_profil("gestionnaire_stock")
    assert compte.check_password("Un-Mot-De-Passe-Solide-42")
    assert EvenementSecurite.objects.filter(type="droits", objet_id=str(compte.pk)).exists()


def test_compte_exige_un_agent(equipe, connecter):
    reponse = connecter(equipe["admin_fonc"]).post(
        "/administration/comptes/nouveau/",
        {
            "username": "sansagent",
            "mot_de_passe1": "Un-Mot-De-Passe-Solide-42",
            "mot_de_passe2": "Un-Mot-De-Passe-Solide-42",
        },
    )
    assert reponse.status_code == 200 and not Utilisateur.objects.filter(username="sansagent").exists()


def test_admin_fonctionnel_ne_peut_pas_attribuer_admin_technique(equipe, connecter, organisation):
    agent = _creer_agent(organisation)
    reponse = connecter(equipe["admin_fonc"]).post(
        "/administration/comptes/nouveau/",
        {
            "username": "pirate",
            "agent": agent.pk,
            "groups": [Group.objects.get(name="admin_technique").pk],
            "mot_de_passe1": "Un-Mot-De-Passe-Solide-42",
            "mot_de_passe2": "Un-Mot-De-Passe-Solide-42",
        },
    )
    assert reponse.status_code == 200
    assert "Seul l&#x27;administrateur technique" in reponse.content.decode()
    assert not Utilisateur.objects.filter(username="pirate").exists()


def test_personne_ne_modifie_ses_propres_profils(equipe, connecter):
    admin = equipe["admin_tech"]
    connecter(admin).post(
        f"/administration/comptes/{admin.pk}/",
        {
            "username": admin.username,
            "agent": admin.agent_id,
            "is_active": "on",
            "groups": [Group.objects.get(name="direction").pk],
        },
    )
    assert set(admin.groups.values_list("name", flat=True)) == {"admin_technique"}


def test_on_ne_desactive_pas_son_propre_compte(equipe, connecter):
    admin = equipe["admin_tech"]
    reponse = connecter(admin).post(
        f"/administration/comptes/{admin.pk}/",
        {
            "username": admin.username,
            "agent": admin.agent_id,
        },
    )
    assert reponse.status_code == 200
    assert Utilisateur.objects.get(pk=admin.pk).is_active


def test_reinitialisation_mot_de_passe(equipe, connecter):
    cible = equipe["agent"]
    reponse = connecter(equipe["admin_tech"]).post(
        f"/administration/comptes/{cible.pk}/mot-de-passe/",
        {
            "mot_de_passe1": "Nouveau-Mot-De-Passe-77",
            "mot_de_passe2": "Nouveau-Mot-De-Passe-77",
        },
    )
    assert reponse.status_code == 302
    cible.refresh_from_db()
    assert cible.check_password("Nouveau-Mot-De-Passe-77")
