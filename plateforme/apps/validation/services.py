"""Moteur de validation générique (cahier des charges §3.3).

Un module métier soumet un objet avec ``soumettre`` puis réagit à la fin du
circuit en définissant sur son modèle la méthode
``validation_terminee(self, instance)``.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.alertes import services as alertes
from apps.alertes.models import Alerte
from apps.journal.services import journaliser

from .models import Circuit, Decision, Delegation, EtapeCircuit, InstanceValidation


def _cle_alerte(instance):
    return f"validation:{instance.pk}"


def chef_pour(demandeur):
    """Chef de service du demandeur. Si le demandeur dirige lui-même son
    service, la demande remonte au chef du service parent."""
    service = demandeur.service
    while service is not None:
        chef = service.chef
        utilisateur_chef = getattr(chef, "utilisateur", None) if chef is not None else None
        if utilisateur_chef is not None and utilisateur_chef.pk != demandeur.pk and utilisateur_chef.is_active:
            return utilisateur_chef
        service = service.parent
    return None


def valideurs_titulaires(instance, etape=None):
    """Utilisateurs habilités par le circuit à décider à cette étape
    (hors délégations), le demandeur étant toujours exclu."""
    etape = etape or instance.etape_courante
    Utilisateur = get_user_model()
    if etape is None:
        return Utilisateur.objects.none()
    if etape.mode == EtapeCircuit.MODE_CHEF_SERVICE:
        chef = chef_pour(instance.demandeur)
        ids = [chef.pk] if chef else []
        titulaires = Utilisateur.objects.filter(pk__in=ids)
    elif etape.mode == EtapeCircuit.MODE_PROFIL:
        titulaires = Utilisateur.objects.filter(groups=etape.profil)
    else:
        titulaires = Utilisateur.objects.filter(pk=etape.utilisateur_id)
    return titulaires.filter(is_active=True).exclude(pk=instance.demandeur_id).distinct()


def _delegations_actives(date=None):
    date = date or timezone.localdate()
    return Delegation.objects.filter(actif=True, debut__lte=date, fin__gte=date)


def valideurs_effectifs(instance):
    """Titulaires + délégataires actifs de ces titulaires."""
    titulaires = list(valideurs_titulaires(instance))
    delegataires = [
        d.delegataire
        for d in _delegations_actives().filter(delegant__in=titulaires).select_related("delegataire")
        if d.delegataire_id != instance.demandeur_id and d.delegataire.is_active
    ]
    return set(titulaires) | set(delegataires)


def peut_decider(utilisateur, instance):
    """Renvoie (autorisé, délégant). Nul ne valide sa propre demande, même
    avec le profil valideur ou par délégation."""
    if instance.statut != InstanceValidation.EN_COURS or utilisateur.pk == instance.demandeur_id:
        return False, None
    titulaires = valideurs_titulaires(instance)
    if titulaires.filter(pk=utilisateur.pk).exists():
        return True, None
    delegation = (
        _delegations_actives()
        .filter(delegataire=utilisateur, delegant__in=titulaires)
        .select_related("delegant")
        .first()
    )
    if delegation is not None:
        return True, delegation.delegant
    return False, None


def instances_a_valider(utilisateur):
    en_cours = InstanceValidation.objects.filter(statut=InstanceValidation.EN_COURS).select_related(
        "circuit",
        "etape_courante",
        "demandeur__agent__service",
        "content_type",
    )
    return [i for i in en_cours if peut_decider(utilisateur, i)[0]]


def peut_consulter(utilisateur, instance):
    if utilisateur.has_perm("validation.view_instancevalidation"):
        return True
    if utilisateur.pk == instance.demandeur_id or peut_decider(utilisateur, instance)[0]:
        return True
    return instance.decisions.filter(valideur=utilisateur).exists()


def _etape_suivante(circuit, montant, apres_ordre=0):
    for etape in circuit.etapes.filter(actif=True, ordre__gt=apres_ordre).order_by("ordre"):
        if etape.s_applique(montant):
            return etape
    return None


def _notifier_valideurs(instance):
    alertes.resoudre(_cle_alerte(instance))
    if instance.statut != InstanceValidation.EN_COURS:
        return
    alertes.lever(
        _cle_alerte(instance),
        valideurs_effectifs(instance),
        titre=f"À valider : {instance.objet}",
        message=f"{instance.circuit} — étape « {instance.etape_courante.libelle} », demandé par {instance.demandeur}.",
        code_regle="validation_en_attente",
        gravite=Alerte.ATTENTION,
        lien=instance.get_absolute_url(),
        objet=instance,
    )


def _verifier_valideurs(instance, etape):
    if not valideurs_titulaires(instance, etape).exists():
        raise ValidationError(
            f"Aucun valideur disponible pour l'étape « {etape.libelle} » du circuit « {instance.circuit} ». "
            "L'administrateur fonctionnel doit compléter le circuit ou les chefs de service."
        )


@transaction.atomic
def soumettre(objet, demandeur, code_circuit, montant=None, request=None):
    try:
        circuit = Circuit.objects.get(code=code_circuit, actif=True)
    except Circuit.DoesNotExist:
        raise ValidationError(
            f"Aucun circuit de validation actif « {code_circuit} ». Contactez l'administrateur fonctionnel."
        ) from None
    etape = _etape_suivante(circuit, montant)
    if etape is None:
        raise ValidationError(f"Le circuit « {circuit} » n'a aucune étape applicable.")
    instance = InstanceValidation(
        circuit=circuit,
        content_type=ContentType.objects.get_for_model(objet),
        object_id=objet.pk,
        demandeur=demandeur,
        montant=montant,
        etape_courante=etape,
    )
    _verifier_valideurs(instance, etape)
    try:
        with transaction.atomic():
            instance.save()
    except IntegrityError:
        raise ValidationError("Cet élément a déjà une validation en cours.") from None
    _notifier_valideurs(instance)
    return instance


def _terminer(instance, statut):
    instance.statut = statut
    instance.terminee_le = timezone.now()
    instance.etape_courante = None
    instance.save(update_fields=["statut", "terminee_le", "etape_courante"])
    alertes.resoudre(_cle_alerte(instance))
    alertes.lever(
        f"validation_resultat:{instance.pk}",
        [instance.demandeur],
        titre=f"{instance.get_statut_display()} : {instance.objet}",
        code_regle="validation_resultat",
        gravite=Alerte.INFO,
        lien=instance.get_absolute_url(),
        objet=instance,
    )
    rappel = getattr(instance.objet, "validation_terminee", None)
    if callable(rappel):
        rappel(instance)


@transaction.atomic
def decider(instance, valideur, decision, motif="", request=None):
    instance = InstanceValidation.objects.select_for_update().select_related("circuit").get(pk=instance.pk)
    autorise, delegant = peut_decider(valideur, instance)
    if not autorise:
        raise PermissionDenied("Vous n'êtes pas valideur de cette étape.")
    motif = (motif or "").strip()
    if decision in (Decision.REJETER, Decision.RENVOYER) and not motif:
        raise ValidationError("Le motif est obligatoire pour un rejet ou un renvoi.")
    if decision not in dict(Decision.CHOIX):
        raise ValidationError("Décision inconnue.")

    etape = instance.etape_courante
    suivante = None
    if decision == Decision.VALIDER:
        suivante = _etape_suivante(instance.circuit, instance.montant, etape.ordre)
        if suivante is not None:
            _verifier_valideurs(instance, suivante)

    Decision.objects.create(
        instance=instance,
        etape=etape,
        valideur=valideur,
        par_delegation_de=delegant,
        decision=decision,
        motif=motif,
    )
    journaliser(
        request,
        "validation",
        f"{dict(Decision.CHOIX)[decision]} — {instance.circuit} — {instance.objet}"
        + (f" (par délégation de {delegant})" if delegant else ""),
        utilisateur=valideur,
        objet=instance,
    )
    if decision == Decision.VALIDER and suivante is not None:
        instance.etape_courante = suivante
        instance.etape_depuis = timezone.now()
        instance.save(update_fields=["etape_courante", "etape_depuis"])
        _notifier_valideurs(instance)
    elif decision == Decision.VALIDER:
        _terminer(instance, InstanceValidation.VALIDEE)
    elif decision == Decision.REJETER:
        _terminer(instance, InstanceValidation.REJETEE)
    else:
        _terminer(instance, InstanceValidation.RENVOYEE)
    return instance


@transaction.atomic
def annuler(instance, utilisateur, motif, request=None):
    instance = InstanceValidation.objects.select_for_update().get(pk=instance.pk)
    if instance.statut != InstanceValidation.EN_COURS:
        raise ValidationError("Seule une validation en cours peut être annulée.")
    if utilisateur.pk != instance.demandeur_id:
        raise PermissionDenied("Seul le demandeur peut annuler sa demande.")
    if not (motif or "").strip():
        raise ValidationError("Le motif d'annulation est obligatoire.")
    journaliser(
        request,
        "validation",
        f"Annulation — {instance.circuit} — {instance.objet} : {motif}"[:500],
        utilisateur=utilisateur,
        objet=instance,
    )
    instance.motif_annulation = motif.strip()
    instance.save(update_fields=["motif_annulation"])
    _terminer(instance, InstanceValidation.ANNULEE)
    return instance
