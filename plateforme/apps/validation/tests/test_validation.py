from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.alertes.models import Alerte
from apps.journal.models import EvenementSecurite
from apps.validation import services
from apps.validation.models import Decision, Delegation, EtapeCircuit, InstanceValidation


@pytest.fixture
def objet(organisation):
    # Le moteur est générique : n'importe quel objet métier peut être validé.
    return organisation["site"]


def test_circuit_complet_deux_niveaux(equipe, circuit, objet):
    instance = services.soumettre(objet, equipe["agent"], "mission")
    assert instance.etape_courante.ordre == 1
    assert services.valideurs_effectifs(instance) == {equipe["chef_prog"]}
    # Le valideur du niveau 2 ne peut pas sauter le niveau 1.
    assert services.peut_decider(equipe["chef_log"], instance) == (False, None)

    services.decider(instance, equipe["chef_prog"], Decision.VALIDER)
    instance.refresh_from_db()
    assert instance.etape_courante.ordre == 2
    services.decider(instance, equipe["chef_log"], Decision.VALIDER)
    instance.refresh_from_db()
    assert instance.statut == InstanceValidation.VALIDEE and instance.etape_courante is None
    assert EvenementSecurite.objects.filter(type="validation").count() == 2


def test_nul_ne_valide_sa_propre_demande(equipe, circuit, objet):
    # Le chef de service demande : sa propre étape remonte au chef du service parent.
    instance = services.soumettre(objet, equipe["chef_prog"], "mission")
    assert services.peut_decider(equipe["chef_prog"], instance) == (False, None)
    assert services.valideurs_effectifs(instance) == {equipe["directeur"]}
    with pytest.raises(PermissionDenied):
        services.decider(instance, equipe["chef_prog"], Decision.VALIDER)


def test_etape_sans_autre_valideur_que_le_demandeur(equipe, circuit, objet):
    # Le responsable logistique demande : l'étape 1 remonte au directeur, mais
    # l'étape 2 (profil responsable_logistique) n'a pas d'autre titulaire que
    # lui. La validation de l'étape 1 est refusée plutôt que de laisser la
    # demande bloquée sans valideur, et rien n'est enregistré.
    instance = services.soumettre(objet, equipe["chef_log"], "mission")
    assert not services.peut_decider(equipe["chef_log"], instance)[0]
    with pytest.raises(ValidationError, match="Aucun valideur disponible"):
        services.decider(instance, equipe["directeur"], Decision.VALIDER)
    assert not Decision.objects.exists()
    instance.refresh_from_db()
    assert instance.statut == InstanceValidation.EN_COURS and instance.etape_courante.ordre == 1


def test_rejet_et_renvoi_exigent_un_motif(equipe, circuit, objet):
    instance = services.soumettre(objet, equipe["agent"], "mission")
    with pytest.raises(ValidationError, match="motif est obligatoire"):
        services.decider(instance, equipe["chef_prog"], Decision.REJETER, "  ")
    services.decider(instance, equipe["chef_prog"], Decision.RENVOYER, "Préciser les dates")
    instance.refresh_from_db()
    assert instance.statut == InstanceValidation.RENVOYEE
    # Après un renvoi, une nouvelle soumission est possible.
    assert services.soumettre(objet, equipe["agent"], "mission").statut == InstanceValidation.EN_COURS


def test_une_seule_validation_en_cours_par_objet(equipe, circuit, objet):
    services.soumettre(objet, equipe["agent"], "mission")
    with pytest.raises(ValidationError, match="déjà une validation en cours"):
        services.soumettre(objet, equipe["agent"], "mission")


def test_decision_definitive(equipe, circuit, objet):
    instance = services.soumettre(objet, equipe["agent"], "mission")
    services.decider(instance, equipe["chef_prog"], Decision.REJETER, "Hors budget")
    with pytest.raises(PermissionDenied):
        services.decider(instance, equipe["chef_prog"], Decision.VALIDER)


def test_seuil_de_montant(equipe, circuit, objet):
    EtapeCircuit.objects.create(
        circuit=circuit,
        ordre=3,
        libelle="Direction",
        mode=EtapeCircuit.MODE_UTILISATEUR,
        utilisateur=equipe["directeur"],
        seuil_montant=1_000_000,
    )
    petite = services.soumettre(objet, equipe["agent"], "mission", montant=200_000)
    services.decider(petite, equipe["chef_prog"], Decision.VALIDER)
    services.decider(petite, equipe["chef_log"], Decision.VALIDER)
    petite.refresh_from_db()
    assert petite.statut == InstanceValidation.VALIDEE

    grosse = services.soumettre(equipe["agent2"].agent, equipe["agent2"], "mission", montant=5_000_000)
    services.decider(grosse, equipe["chef_prog"], Decision.VALIDER)
    services.decider(grosse, equipe["chef_log"], Decision.VALIDER)
    grosse.refresh_from_db()
    assert grosse.statut == InstanceValidation.EN_COURS and grosse.etape_courante.ordre == 3


def test_delegation(equipe, circuit, objet):
    aujourd_hui = timezone.localdate()
    Delegation.objects.create(
        delegant=equipe["chef_prog"],
        delegataire=equipe["agent2"],
        debut=aujourd_hui,
        fin=aujourd_hui + timedelta(days=5),
    )
    instance = services.soumettre(objet, equipe["agent"], "mission")
    assert services.peut_decider(equipe["agent2"], instance) == (True, equipe["chef_prog"])
    services.decider(instance, equipe["agent2"], Decision.VALIDER)
    decision = Decision.objects.get()
    assert decision.valideur == equipe["agent2"] and decision.par_delegation_de == equipe["chef_prog"]


def test_delegation_ne_permet_pas_de_valider_sa_propre_demande(equipe, circuit, objet):
    aujourd_hui = timezone.localdate()
    Delegation.objects.create(
        delegant=equipe["chef_prog"], delegataire=equipe["agent"], debut=aujourd_hui, fin=aujourd_hui
    )
    instance = services.soumettre(objet, equipe["agent"], "mission")
    assert services.peut_decider(equipe["agent"], instance) == (False, None)


def test_delegation_expiree_sans_effet(equipe, circuit, objet):
    hier = timezone.localdate() - timedelta(days=1)
    Delegation.objects.create(delegant=equipe["chef_prog"], delegataire=equipe["agent2"], debut=hier, fin=hier)
    instance = services.soumettre(objet, equipe["agent"], "mission")
    assert not services.peut_decider(equipe["agent2"], instance)[0]


def test_alertes_suivent_le_circuit(equipe, circuit, objet):
    instance = services.soumettre(objet, equipe["agent"], "mission")
    assert Alerte.objects.filter(destinataire=equipe["chef_prog"], active=True).count() == 1
    services.decider(instance, equipe["chef_prog"], Decision.VALIDER)
    assert not Alerte.objects.filter(destinataire=equipe["chef_prog"], active=True).exists()
    assert Alerte.objects.filter(destinataire=equipe["chef_log"], active=True).count() == 1
    services.decider(instance, equipe["chef_log"], Decision.VALIDER)
    assert not Alerte.objects.filter(destinataire=equipe["chef_log"], active=True).exists()
    resultat = Alerte.objects.get(destinataire=equipe["agent"], active=True)
    assert resultat.gravite == Alerte.INFO and "Validée" in resultat.titre


def test_annulation_par_le_demandeur_seulement(equipe, circuit, objet):
    instance = services.soumettre(objet, equipe["agent"], "mission")
    with pytest.raises(PermissionDenied):
        services.annuler(instance, equipe["chef_prog"], "test")
    with pytest.raises(ValidationError):
        services.annuler(instance, equipe["agent"], "")
    services.annuler(instance, equipe["agent"], "Mission reportée")
    instance.refresh_from_db()
    assert instance.statut == InstanceValidation.ANNULEE and instance.motif_annulation == "Mission reportée"


def test_rappel_au_module_metier(equipe, circuit, objet, monkeypatch):
    appels = []
    monkeypatch.setattr(type(objet), "validation_terminee", lambda self, i: appels.append(i.statut), raising=False)
    instance = services.soumettre(objet, equipe["agent"], "mission")
    services.decider(instance, equipe["chef_prog"], Decision.REJETER, "Non")
    assert appels == [InstanceValidation.REJETEE]


# --- Écrans -----------------------------------------------------------------


def test_ecran_decision(equipe, circuit, objet, connecter):
    instance = services.soumettre(objet, equipe["agent"], "mission")
    client = connecter(equipe["chef_prog"])
    assert str(objet) in client.get("/validations/").content.decode()
    reponse = client.post(f"/validations/{instance.pk}/", {"decision": "rejeter", "motif": ""})
    assert reponse.status_code == 200 and "motif est obligatoire" in reponse.content.decode()
    assert client.post(f"/validations/{instance.pk}/", {"decision": "valider"}).status_code == 302


def test_detail_interdit_aux_tiers(equipe, circuit, objet, connecter):
    instance = services.soumettre(objet, equipe["agent"], "mission")
    assert connecter(equipe["agent2"]).get(f"/validations/{instance.pk}/").status_code == 403
    assert connecter(equipe["auditeur"]).get(f"/validations/{instance.pk}/").status_code == 200


def test_tiers_ne_peut_pas_decider_par_requete_forgee(equipe, circuit, objet, connecter):
    instance = services.soumettre(objet, equipe["agent"], "mission")
    reponse = connecter(equipe["auditeur"]).post(f"/validations/{instance.pk}/", {"decision": "valider"})
    assert reponse.status_code == 403
    assert not Decision.objects.exists()


def test_ecran_delegation(equipe, connecter):
    client = connecter(equipe["chef_prog"])
    aujourd_hui = timezone.localdate()
    reponse = client.post(
        "/validations/delegations/",
        {
            "delegataire": equipe["agent2"].pk,
            "debut": aujourd_hui.isoformat(),
            "fin": aujourd_hui.isoformat(),
        },
    )
    assert reponse.status_code == 302
    delegation = Delegation.objects.get()
    assert delegation.delegant == equipe["chef_prog"]
    client.post("/validations/delegations/", {"terminer": delegation.pk})
    delegation.refresh_from_db()
    assert delegation.actif is False
