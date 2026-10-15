from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from apps.noyau.models import ModeleBase


class Circuit(ModeleBase):
    """Circuit de validation paramétrable par l'administrateur fonctionnel.

    ``code`` est le nom par lequel un module demande un circuit
    (ex. « mission », « demande_materiel »).
    """

    code = models.SlugField("code", max_length=50, unique=True)
    libelle = models.CharField("libellé", max_length=150)

    class Meta:
        ordering = ["code"]
        verbose_name = "circuit de validation"
        verbose_name_plural = "circuits de validation"

    def __str__(self):
        return self.libelle


class EtapeCircuit(ModeleBase):
    MODE_CHEF_SERVICE = "chef_service"
    MODE_PROFIL = "profil"
    MODE_UTILISATEUR = "utilisateur"
    MODES = [
        (MODE_CHEF_SERVICE, "Chef de service du demandeur"),
        (MODE_PROFIL, "Tout titulaire d'un profil"),
        (MODE_UTILISATEUR, "Utilisateur désigné"),
    ]

    circuit = models.ForeignKey(Circuit, verbose_name="circuit", on_delete=models.PROTECT, related_name="etapes")
    ordre = models.PositiveSmallIntegerField("ordre")
    libelle = models.CharField("libellé", max_length=150)
    mode = models.CharField("valideur", max_length=20, choices=MODES)
    profil = models.ForeignKey(Group, verbose_name="profil", on_delete=models.PROTECT, null=True, blank=True)
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilisateur désigné",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    seuil_montant = models.PositiveBigIntegerField(
        "seuil de montant (XOF)",
        null=True,
        blank=True,
        help_text="Si renseigné, l'étape ne s'applique qu'aux demandes d'un montant supérieur ou égal.",
    )

    class Meta:
        ordering = ["circuit", "ordre"]
        verbose_name = "étape de circuit"
        constraints = [models.UniqueConstraint(fields=["circuit", "ordre"], name="etape_ordre_unique")]

    def __str__(self):
        return f"{self.ordre}. {self.libelle}"

    def clean(self):
        if self.mode == self.MODE_PROFIL and not self.profil_id:
            raise ValidationError({"profil": "Choisissez le profil valideur."})
        if self.mode == self.MODE_UTILISATEUR and not self.utilisateur_id:
            raise ValidationError({"utilisateur": "Choisissez l'utilisateur valideur."})

    def s_applique(self, montant):
        return self.seuil_montant is None or (montant is not None and montant >= self.seuil_montant)


class InstanceValidation(models.Model):
    EN_COURS = "en_cours"
    VALIDEE = "validee"
    REJETEE = "rejetee"
    RENVOYEE = "renvoyee"
    ANNULEE = "annulee"
    STATUTS = [
        (EN_COURS, "En cours"),
        (VALIDEE, "Validée"),
        (REJETEE, "Rejetée"),
        (RENVOYEE, "Renvoyée pour correction"),
        (ANNULEE, "Annulée"),
    ]

    circuit = models.ForeignKey(Circuit, on_delete=models.PROTECT, related_name="instances")
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveBigIntegerField()
    objet = GenericForeignKey("content_type", "object_id")
    demandeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    montant = models.PositiveBigIntegerField("montant (XOF)", null=True, blank=True)
    etape_courante = models.ForeignKey(EtapeCircuit, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    statut = models.CharField(max_length=20, choices=STATUTS, default=EN_COURS, db_index=True)
    soumise_le = models.DateTimeField("soumise le", auto_now_add=True)
    terminee_le = models.DateTimeField("terminée le", null=True, blank=True)
    etape_depuis = models.DateTimeField("à l'étape depuis", auto_now_add=True)
    motif_annulation = models.TextField("motif d'annulation", blank=True)

    class Meta:
        ordering = ["-soumise_le"]
        verbose_name = "validation"
        indexes = [models.Index(fields=["content_type", "object_id"])]
        constraints = [
            # Une seule validation en cours à la fois pour un même objet.
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                condition=models.Q(statut="en_cours"),
                name="une_validation_en_cours_par_objet",
            )
        ]

    def __str__(self):
        return f"{self.circuit} — {self.objet}"

    def get_absolute_url(self):
        return reverse("validation:detail", args=[self.pk])


class Decision(models.Model):
    VALIDER = "valider"
    REJETER = "rejeter"
    RENVOYER = "renvoyer"
    CHOIX = [(VALIDER, "Valider"), (REJETER, "Rejeter"), (RENVOYER, "Renvoyer pour correction")]

    instance = models.ForeignKey(InstanceValidation, on_delete=models.PROTECT, related_name="decisions")
    etape = models.ForeignKey(EtapeCircuit, on_delete=models.PROTECT, related_name="+")
    valideur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    par_delegation_de = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    decision = models.CharField(max_length=10, choices=CHOIX)
    motif = models.TextField("motif", blank=True)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["horodatage"]
        verbose_name = "décision"

    def __str__(self):
        return f"{self.get_decision_display()} — {self.valideur}"


class Delegation(ModeleBase):
    delegant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="délégant",
        on_delete=models.PROTECT,
        related_name="delegations_donnees",
    )
    delegataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="délégataire",
        on_delete=models.PROTECT,
        related_name="delegations_recues",
    )
    debut = models.DateField("du")
    fin = models.DateField("au")

    class Meta:
        ordering = ["-debut"]
        verbose_name = "délégation"
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__gte=models.F("debut")), name="delegation_periode_valide"),
            models.CheckConstraint(
                condition=~models.Q(delegant=models.F("delegataire")),
                name="delegation_pas_a_soi_meme",
            ),
        ]

    def __str__(self):
        return f"{self.delegant} → {self.delegataire} ({self.debut:%d/%m/%Y} – {self.fin:%d/%m/%Y})"
