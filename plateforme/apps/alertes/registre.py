"""Registre des règles d'alerte calculées périodiquement.

Chaque module enregistre ses règles avec ``@regle("code")`` ; la tâche
nocturne ``calculer_alertes`` les exécute toutes. Une règle lève les alertes
encore justifiées et résout celles dont la cause a disparu.
"""

import logging

REGLES = {}
journal = logging.getLogger(__name__)


def regle(code):
    def enregistrer(fonction):
        REGLES[code] = fonction
        return fonction

    return enregistrer


def calculer_alertes():
    resultats = {}
    for code, fonction in REGLES.items():
        try:
            resultats[code] = fonction()
        except Exception:  # une règle en erreur ne doit pas bloquer les autres
            journal.exception("Échec de la règle d'alerte %s", code)
            resultats[code] = "erreur"
    return resultats
