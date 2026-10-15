from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Alerte(models.Model):
    """Alerte adressée à un utilisateur.

    Une alerte d'attention ou critique reste active tant que sa cause n'est pas
    traitée (``resoudre``) : la prise en compte la marque seulement comme lue.
    Une alerte d'information disparaît dès sa prise en compte.
    """

    INFO = 0
    ATTENTION = 1
    CRITIQUE = 2
    GRAVITES = [(INFO, "Information"), (ATTENTION, "Attention"), (CRITIQUE, "Critique")]

    code_regle = models.CharField("règle", max_length=60, db_index=True)
    cle = models.CharField("clé", max_length=150, db_index=True)
    gravite = models.PositiveSmallIntegerField("gravité", choices=GRAVITES, default=ATTENTION)
    titre = models.CharField("titre", max_length=200)
    message = models.TextField("message", blank=True)
    lien = models.CharField("lien", max_length=300, blank=True)
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="destinataire",
        on_delete=models.PROTECT,
        related_name="alertes",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    objet = GenericForeignKey("content_type", "object_id")
    active = models.BooleanField(default=True, db_index=True)
    cree_le = models.DateTimeField("créée le", auto_now_add=True)
    prise_en_compte_le = models.DateTimeField("prise en compte le", null=True, blank=True)
    resolue_le = models.DateTimeField("résolue le", null=True, blank=True)

    class Meta:
        ordering = ["-gravite", "-cree_le"]
        verbose_name = "alerte"
        constraints = [
            models.UniqueConstraint(
                fields=["cle", "destinataire"],
                condition=models.Q(active=True),
                name="alerte_active_unique",
            )
        ]

    def __str__(self):
        return self.titre
