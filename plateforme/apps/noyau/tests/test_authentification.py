from django.conf import settings
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.journal.models import EvenementSecurite
from conftest import MOT_DE_PASSE


def _connexion(client, identifiant, mot_de_passe):
    return client.post("/connexion/", {"username": identifiant, "password": mot_de_passe})


def test_connexion_reussie_journalisee(client, equipe):
    reponse = _connexion(client, "agent", MOT_DE_PASSE)
    assert reponse.status_code == 302 and reponse.url == "/"
    assert EvenementSecurite.objects.filter(type="connexion", utilisateur=equipe["agent"]).exists()


def test_verrouillage_apres_cinq_echecs(client, equipe):
    for _ in range(5):
        _connexion(client, "agent", "mauvais-mot-de-passe")
    assert EvenementSecurite.objects.filter(type="connexion_echec", identifiant_saisi="agent").count() >= 4
    # Même avec le bon mot de passe, le compte reste verrouillé.
    reponse = _connexion(client, "agent", MOT_DE_PASSE)
    assert reponse.status_code == 429
    assert "verrouillé" in reponse.content.decode()
    assert EvenementSecurite.objects.filter(type="verrouillage", identifiant_saisi="agent").exists()


def test_reglages_de_session():
    assert settings.SESSION_COOKIE_AGE == 1800
    assert settings.SESSION_SAVE_EVERY_REQUEST
    assert settings.SESSION_COOKIE_HTTPONLY


def test_mot_de_passe_trop_court_refuse(equipe, connecter):
    client = connecter(equipe["admin_fonc"])
    reponse = client.post(
        "/administration/comptes/nouveau/",
        {
            "username": "nouveau",
            "agent": "",
            "mot_de_passe1": "court1",
            "mot_de_passe2": "court1",
        },
    )
    assert reponse.status_code == 200
    assert "au minimum 12 caractères" in reponse.content.decode()


def test_admin_doit_activer_la_double_authentification(client, equipe):
    _connexion(client, "admin_fonc", MOT_DE_PASSE)
    reponse = client.get("/administration/agents/")
    assert reponse.status_code == 302 and reponse.url == "/double-authentification/activer/"


def test_agent_non_soumis_a_la_double_authentification(client, equipe):
    _connexion(client, "agent", MOT_DE_PASSE)
    assert client.get("/").status_code == 200


def test_activation_puis_verification_otp(client, equipe):
    _connexion(client, "admin_fonc", MOT_DE_PASSE)
    assert client.get("/double-authentification/activer/").status_code == 200
    appareil = TOTPDevice.objects.get(user=equipe["admin_fonc"], confirmed=False)
    assert client.post("/double-authentification/activer/", {"code": "000000"}).status_code == 200
    # Après un échec, django-otp impose un court délai avant tout nouvel essai ;
    # on le lève ici pour ne pas attendre dans le test.
    appareil.refresh_from_db()
    appareil.throttle_reset()
    code = f"{TOTP(appareil.bin_key, appareil.step, appareil.t0, appareil.digits).token():06d}"
    reponse = client.post("/double-authentification/activer/", {"code": code})
    assert reponse.status_code == 302
    assert client.get("/administration/agents/").status_code == 200

    # À la connexion suivante, seul le code est demandé.
    client.logout()
    _connexion(client, "admin_fonc", MOT_DE_PASSE)
    assert client.get("/").url == "/double-authentification/verifier/"


def test_redirection_externe_refusee_apres_otp(client, equipe):
    appareil = TOTPDevice.objects.create(user=equipe["admin_fonc"], name="t", confirmed=True)
    _connexion(client, "admin_fonc", MOT_DE_PASSE)
    code = f"{TOTP(appareil.bin_key, appareil.step, appareil.t0, appareil.digits).token():06d}"
    reponse = client.post("/double-authentification/verifier/?next=https://exemple.invalid/", {"code": code})
    assert reponse.status_code == 302 and reponse.url == "/"
