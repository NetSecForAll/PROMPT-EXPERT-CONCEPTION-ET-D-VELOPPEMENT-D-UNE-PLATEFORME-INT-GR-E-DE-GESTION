from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class ModeleBase(models.Model):
    """Champs système communs à toutes les tables métier.

    Aucune ligne référencée n'est supprimée physiquement : on la désactive
    (champ ``actif``). Le champ ``version`` sert à détecter les modifications
    concurrentes sur les formulaires.
    """

    cree_le = models.DateTimeField("créé le", auto_now_add=True)
    modifie_le = models.DateTimeField("modifié le", auto_now=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="créé par",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="modifié par",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    actif = models.BooleanField("actif", default=True)
    version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        abstract = True


class Site(ModeleBase):
    code = models.CharField("code", max_length=20, unique=True)
    nom = models.CharField("nom", max_length=150)
    adresse = models.CharField("adresse", max_length=255, blank=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "site"

    def __str__(self):
        return f"{self.code} — {self.nom}"

    def get_absolute_url(self):
        return reverse("noyau:site_modifier", args=[self.pk])


class Service(ModeleBase):
    code = models.CharField("code", max_length=20, unique=True)
    nom = models.CharField("nom", max_length=150)
    site = models.ForeignKey(Site, verbose_name="site", on_delete=models.PROTECT, related_name="services")
    parent = models.ForeignKey(
        "self",
        verbose_name="service parent",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sous_services",
    )
    chef = models.ForeignKey(
        "Agent",
        verbose_name="chef de service",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="services_diriges",
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "service"

    def __str__(self):
        return f"{self.code} — {self.nom}"

    def get_absolute_url(self):
        return reverse("noyau:service_modifier", args=[self.pk])

    def clean(self):
        # Une hiérarchie de services ne doit jamais boucler.
        noeud = self.parent
        vus = set()
        while noeud is not None:
            if noeud.pk == self.pk or noeud.pk in vus:
                raise ValidationError({"parent": "Ce service parent créerait une boucle dans la hiérarchie."})
            vus.add(noeud.pk)
            noeud = noeud.parent


class Agent(ModeleBase):
    matricule = models.CharField("matricule", max_length=30, unique=True)
    nom = models.CharField("nom", max_length=100)
    prenom = models.CharField("prénom", max_length=100)
    fonction = models.CharField("fonction", max_length=150, blank=True)
    service = models.ForeignKey(Service, verbose_name="service", on_delete=models.PROTECT, related_name="agents")
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("courriel", blank=True)

    class Meta:
        ordering = ["nom", "prenom"]
        verbose_name = "agent"

    def __str__(self):
        return f"{self.nom.upper()} {self.prenom} ({self.matricule})"

    def get_absolute_url(self):
        return reverse("noyau:agent_modifier", args=[self.pk])


class Utilisateur(AbstractUser):
    """Compte de connexion. Un compte est rattaché à un agent de l'organisation.

    Seul le compte technique initial (créé par ``createsuperuser``) peut
    exister sans agent ; les formulaires de l'application imposent l'agent.
    """

    agent = models.OneToOneField(
        Agent,
        verbose_name="agent",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="utilisateur",
    )

    class Meta:
        ordering = ["username"]
        verbose_name = "utilisateur"

    def __str__(self):
        if self.agent_id:
            return f"{self.agent.prenom} {self.agent.nom.upper()}"
        return self.get_full_name() or self.username

    def get_absolute_url(self):
        return reverse("noyau:utilisateur_modifier", args=[self.pk])

    @property
    def codes_profils(self):
        if not hasattr(self, "_codes_profils"):
            self._codes_profils = set(self.groups.values_list("name", flat=True))
        return self._codes_profils

    def a_profil(self, *codes):
        return bool(self.codes_profils.intersection(codes))

    @property
    def service(self):
        return self.agent.service if self.agent_id else None


class Profil(Group):
    """Vue « profil » sur les groupes Django (libellé lisible)."""

    class Meta:
        proxy = True
        verbose_name = "profil"


class Parametre(ModeleBase):
    """Paramètre fonctionnel modifiable par l'administrateur fonctionnel."""

    cle = models.CharField("clé", max_length=100, unique=True)
    valeur = models.CharField("valeur", max_length=500)
    description = models.CharField("description", max_length=255, blank=True)

    class Meta:
        ordering = ["cle"]
        verbose_name = "paramètre"

    def __str__(self):
        return self.cle
