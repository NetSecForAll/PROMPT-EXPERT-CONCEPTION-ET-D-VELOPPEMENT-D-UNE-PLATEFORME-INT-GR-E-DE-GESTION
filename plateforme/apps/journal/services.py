from .models import EvenementSecurite


def adresse_ip(request):
    if request is None:
        return None
    # Derrière Nginx, l'adresse réelle est transmise dans X-Real-IP
    # (positionné par notre propre proxy, non par le client).
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def journaliser(request, type_evenement, description, utilisateur=None, objet=None, identifiant_saisi=""):
    if utilisateur is None and request is not None and request.user.is_authenticated:
        utilisateur = request.user
    return EvenementSecurite.objects.create(
        type=type_evenement,
        utilisateur=utilisateur,
        identifiant_saisi=identifiant_saisi[:150],
        adresse_ip=adresse_ip(request),
        chemin=(request.get_full_path()[:500] if request is not None else ""),
        description=description[:500],
        objet_type=objet._meta.label if objet is not None else "",
        objet_id=str(objet.pk) if objet is not None else "",
    )
