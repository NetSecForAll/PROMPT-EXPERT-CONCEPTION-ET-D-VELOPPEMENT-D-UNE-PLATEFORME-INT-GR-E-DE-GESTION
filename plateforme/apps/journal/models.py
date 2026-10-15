from django.conf import settings
from django.db import models


class EvenementSecurite(models.Model):
    """Événement de sécurité. Table en ajout seul : un déclencheur PostgreSQL
    refuse toute modification ou suppression (migration 0002)."""

    TYPES = [
        ("connexion", "Connexion"),
        ("connexion_echec", "Échec de connexion"),
        ("deconnexion", "Déconnexion"),
        ("verrouillage", "Verrouillage de compte"),
        ("otp", "Double authentification"),
        ("otp_echec", "Échec de double authentification"),
        ("acces_refuse", "Accès refusé"),
        ("droits", "Changement de droits ou de mot de passe"),
        ("export", "Export de données"),
        ("validation", "Décision de validation"),
        ("telechargement", "Téléchargement de document"),
    ]

    horodatage = models.DateTimeField("date et heure", auto_now_add=True, db_index=True)
    type = models.CharField("type", max_length=30, choices=TYPES, db_index=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilisateur",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    identifiant_saisi = models.CharField("identifiant saisi", max_length=150, blank=True)
    adresse_ip = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    chemin = models.CharField("page", max_length=500, blank=True)
    description = models.CharField("description", max_length=500)
    objet_type = models.CharField("type d'objet", max_length=100, blank=True)
    objet_id = models.CharField("identifiant d'objet", max_length=50, blank=True)

    class Meta:
        ordering = ["-horodatage"]
        verbose_name = "événement de sécurité"
        verbose_name_plural = "événements de sécurité"

    def __str__(self):
        return f"{self.horodatage:%d/%m/%Y %H:%M} {self.get_type_display()}"
