import pytest
from django.contrib.auth.models import Group
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.noyau.models import Agent, Service, Site, Utilisateur
from apps.validation.models import Circuit, EtapeCircuit

MOT_DE_PASSE = "Test-Mot-De-Passe-2026!"


@pytest.fixture(autouse=True)
def hachage_rapide(settings):
    # Le hachage de production (PBKDF2) est volontairement lent ; inutile en test.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def organisation(db):
    """Siège > Direction (chef : directeur) > Logistique (chef : chef_log) et
    Programmes (chef : chef_prog)."""
    site = Site.objects.create(code="S1", nom="Siège")
    direction = Service.objects.create(code="DG", nom="Direction", site=site)
    logistique = Service.objects.create(code="LOG", nom="Logistique", site=site, parent=direction)
    programmes = Service.objects.create(code="PRG", nom="Programmes", site=site, parent=direction)
    return {"site": site, "direction": direction, "logistique": logistique, "programmes": programmes}


@pytest.fixture
def creer_utilisateur(organisation):
    compteur = {"n": 0}

    def creer(identifiant, service="programmes", profils=(), chef=False):
        compteur["n"] += 1
        agent = Agent.objects.create(
            matricule=f"M{compteur['n']:03d}",
            nom=identifiant.capitalize(),
            prenom="Test",
            service=organisation[service],
        )
        utilisateur = Utilisateur.objects.create_user(username=identifiant, password=MOT_DE_PASSE, agent=agent)
        utilisateur.groups.set(Group.objects.filter(name__in=profils))
        if chef:
            organisation[service].chef = agent
            organisation[service].save()
        return Utilisateur.objects.get(pk=utilisateur.pk)

    return creer


@pytest.fixture
def equipe(creer_utilisateur):
    return {
        "directeur": creer_utilisateur("directeur", "direction", ["direction"], chef=True),
        "chef_prog": creer_utilisateur("chef_prog", "programmes", ["chef_projet"], chef=True),
        "chef_log": creer_utilisateur("chef_log", "logistique", ["responsable_logistique"], chef=True),
        "agent": creer_utilisateur("agent", "programmes", ["agent"]),
        "agent2": creer_utilisateur("agent2", "programmes", ["agent"]),
        "admin_fonc": creer_utilisateur("admin_fonc", "direction", ["admin_fonctionnel"]),
        "admin_tech": creer_utilisateur("admin_tech", "direction", ["admin_technique"]),
        "auditeur": creer_utilisateur("auditeur", "direction", ["auditeur"]),
    }


@pytest.fixture
def circuit(db):
    circuit = Circuit.objects.create(code="mission", libelle="Mission")
    EtapeCircuit.objects.create(
        circuit=circuit, ordre=1, libelle="Chef de service", mode=EtapeCircuit.MODE_CHEF_SERVICE
    )
    EtapeCircuit.objects.create(
        circuit=circuit,
        ordre=2,
        libelle="Logistique",
        mode=EtapeCircuit.MODE_PROFIL,
        profil=Group.objects.get(name="responsable_logistique"),
    )
    return circuit


@pytest.fixture
def connecter(client):
    """Connecte un utilisateur ; pour un administrateur, simule la double
    authentification déjà validée (appareil TOTP confirmé + session vérifiée)."""

    def connecter(utilisateur, verifie=True):
        client.force_login(utilisateur, backend="django.contrib.auth.backends.ModelBackend")
        if verifie:
            appareil, _ = TOTPDevice.objects.get_or_create(user=utilisateur, name="test", defaults={"confirmed": True})
            session = client.session
            session["otp_device_id"] = appareil.persistent_id
            session.save()
        return client

    return connecter
