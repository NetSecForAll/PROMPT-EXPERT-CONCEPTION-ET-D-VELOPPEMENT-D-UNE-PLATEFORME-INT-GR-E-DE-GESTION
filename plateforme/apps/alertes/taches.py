def calculer_alertes():
    """Point d'entrée de la tâche planifiée django-q2."""
    from .registre import calculer_alertes as calculer

    return calculer()
