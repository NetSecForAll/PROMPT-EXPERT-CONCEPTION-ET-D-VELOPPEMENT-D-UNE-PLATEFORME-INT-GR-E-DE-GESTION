from auditlog.models import LogEntry
from django.shortcuts import render

from apps.noyau.vues_generiques import Filtre, ListeView

from .models import EvenementSecurite
from .services import journaliser


def acces_refuse(request, exception=None):
    """Page 403. Exécutée hors de la transaction de la vue : l'événement est
    donc bien conservé même si la vue a été interrompue."""
    journaliser(request, "acces_refuse", f"Accès refusé à {request.path}"[:500])
    return render(request, "403.html", status=403)


class EvenementListeView(ListeView):
    model = EvenementSecurite
    permission_required = "journal.view_evenementsecurite"
    titre = "Journal de sécurité"
    colonnes = [
        ("horodatage", "Date et heure", "horodatage"),
        ("type", "Type", "type"),
        ("utilisateur", "Utilisateur", None),
        ("identifiant_saisi", "Identifiant saisi", None),
        ("adresse_ip", "Adresse IP", None),
        ("description", "Description", None),
    ]
    champs_recherche = ["description", "identifiant_saisi", "utilisateur__username", "chemin"]
    filtres = [Filtre("type", "Type", EvenementSecurite.TYPES)]
    tri_defaut = "-horodatage"

    def get_base_queryset(self):
        return EvenementSecurite.objects.select_related("utilisateur__agent")


def _changements(entree):
    morceaux = []
    for champ, valeur in (entree.changes_dict or {}).items():
        if isinstance(valeur, dict):  # relation plusieurs-à-plusieurs (ex. profils)
            morceaux.append(f"{champ} : {valeur.get('operation', '')} {', '.join(map(str, valeur.get('objects', [])))}")
        else:
            avant, apres = valeur
            morceaux.append(f"{champ} : {avant} → {apres}")
    return " ; ".join(morceaux)[:1000]


class HistoriqueListeView(ListeView):
    """Historique des modifications (valeurs avant et après) enregistré par
    django-auditlog."""

    model = LogEntry
    permission_required = "journal.view_evenementsecurite"
    titre = "Historique des modifications"
    colonnes = [
        ("timestamp", "Date et heure", "timestamp"),
        ("actor", "Auteur", None),
        ("action", "Action", "action"),
        ("content_type.name", "Type d'objet", None),
        ("object_repr", "Objet", None),
        (_changements, "Changements", None),
    ]
    champs_recherche = ["object_repr", "actor__username", "changes_text"]
    filtres = [Filtre("action", "Action", LogEntry.Action.choices)]
    tri_defaut = "-timestamp"

    def get_base_queryset(self):
        return LogEntry.objects.select_related("actor__agent", "content_type")
