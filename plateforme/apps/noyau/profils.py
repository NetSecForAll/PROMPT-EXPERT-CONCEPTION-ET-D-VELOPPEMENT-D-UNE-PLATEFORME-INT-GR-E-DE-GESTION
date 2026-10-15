"""Profils livrés par défaut et leurs permissions (cahier des charges §2 et §9).

Les profils sont des groupes Django dont le nom est le code ci-dessous.
``synchroniser_profils`` crée les groupes manquants et ajoute les permissions
par défaut ; elle ne retire jamais une permission ajoutée par l'administrateur
fonctionnel. Chaque module métier ajoutera ses permissions à ce dictionnaire.
"""

from django.contrib.auth.models import Group, Permission

LIBELLES = {
    "admin_technique": "Administrateur technique",
    "admin_fonctionnel": "Administrateur fonctionnel",
    "direction": "Direction",
    "responsable_logistique": "Responsable logistique",
    "gestionnaire_parc": "Gestionnaire de parc",
    "chauffeur": "Chauffeur",
    "gestionnaire_stock": "Gestionnaire de stock",
    "raf": "Responsable administratif et financier",
    "chef_projet": "Chef de projet",
    "agent": "Agent utilisateur",
    "auditeur": "Auditeur",
}

_LECTURE_REFERENTIELS = ["noyau.view_site", "noyau.view_service", "noyau.view_agent"]
_GESTION_REFERENTIELS = [
    f"noyau.{action}_{modele}"
    for modele in ("site", "service", "agent", "parametre")
    for action in ("view", "add", "change")
]
_GESTION_COMPTES = ["noyau.view_utilisateur", "noyau.add_utilisateur", "noyau.change_utilisateur"]
_GESTION_CIRCUITS = [
    f"validation.{action}_{modele}" for modele in ("circuit", "etapecircuit") for action in ("view", "add", "change")
]

PERMISSIONS = {
    "admin_technique": _GESTION_COMPTES,
    "admin_fonctionnel": _GESTION_COMPTES
    + _GESTION_REFERENTIELS
    + _GESTION_CIRCUITS
    + ["journal.view_evenementsecurite"],
    "direction": _LECTURE_REFERENTIELS + ["validation.view_circuit", "validation.view_instancevalidation"],
    "responsable_logistique": _LECTURE_REFERENTIELS,
    "gestionnaire_parc": _LECTURE_REFERENTIELS,
    "chauffeur": [],
    "gestionnaire_stock": _LECTURE_REFERENTIELS,
    "raf": _LECTURE_REFERENTIELS,
    "chef_projet": _LECTURE_REFERENTIELS,
    "agent": [],
    "auditeur": _LECTURE_REFERENTIELS
    + [
        "noyau.view_utilisateur",
        "noyau.view_parametre",
        "validation.view_circuit",
        "validation.view_etapecircuit",
        "validation.view_instancevalidation",
        "journal.view_evenementsecurite",
    ],
}


def libelle(code):
    return LIBELLES.get(code, code)


def _permission(nom_complet):
    app_label, codename = nom_complet.split(".")
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def synchroniser_profils():
    for code, permissions in PERMISSIONS.items():
        groupe, _ = Group.objects.get_or_create(name=code)
        groupe.permissions.add(*[_permission(p) for p in permissions])
