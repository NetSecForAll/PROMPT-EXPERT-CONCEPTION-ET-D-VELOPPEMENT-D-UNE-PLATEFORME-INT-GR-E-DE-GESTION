"""Charge un jeu de données de démonstration clairement identifié.

Refusé en production. Tous les codes commencent par « DEMO- » et tous les
identifiants de connexion par « demo. » pour qu'aucune donnée de
démonstration ne puisse être confondue avec une donnée réelle.
"""

import secrets

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.noyau.models import Agent, Service, Site, Utilisateur
from apps.validation.models import Circuit, EtapeCircuit

COMPTES = [
    # identifiant, matricule, nom, prénom, fonction, service, profils
    ("demo.admin", "DEMO-001", "Admin", "Fonctionnel", "Administrateur fonctionnel", "DEMO-DG", ["admin_fonctionnel"]),
    ("demo.directeur", "DEMO-002", "Directeur", "Général", "Directeur général", "DEMO-DG", ["direction"]),
    (
        "demo.logistique",
        "DEMO-003",
        "Responsable",
        "Logistique",
        "Chef du service logistique",
        "DEMO-LOG",
        ["responsable_logistique"],
    ),
    (
        "demo.parc",
        "DEMO-004",
        "Gestionnaire",
        "Parc",
        "Gestionnaire du parc automobile",
        "DEMO-LOG",
        ["gestionnaire_parc"],
    ),
    ("demo.stock", "DEMO-005", "Gestionnaire", "Stock", "Magasinier", "DEMO-LOG", ["gestionnaire_stock"]),
    ("demo.raf", "DEMO-006", "Responsable", "Finances", "Responsable administratif et financier", "DEMO-RAF", ["raf"]),
    ("demo.agent", "DEMO-007", "Agent", "Programme", "Chargé de programme", "DEMO-PRG", ["agent"]),
    ("demo.chefprog", "DEMO-008", "Chef", "Programme", "Chef du service programmes", "DEMO-PRG", ["chef_projet"]),
    ("demo.chauffeur", "DEMO-009", "Chauffeur", "Un", "Chauffeur", "DEMO-LOG", ["chauffeur"]),
    ("demo.auditeur", "DEMO-010", "Auditeur", "Interne", "Auditeur interne", "DEMO-DG", ["auditeur"]),
]

CHEFS = {"DEMO-DG": "DEMO-002", "DEMO-LOG": "DEMO-003", "DEMO-RAF": "DEMO-006", "DEMO-PRG": "DEMO-008"}


class Command(BaseCommand):
    help = "Charge des données de démonstration (interdit en production)."

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.EN_PRODUCTION:
            raise CommandError("Les données de démonstration sont interdites en production.")
        if Site.objects.filter(code="DEMO-SIEGE").exists():
            raise CommandError("Les données de démonstration sont déjà chargées.")

        siege = Site.objects.create(code="DEMO-SIEGE", nom="[DÉMO] Siège", adresse="Adresse fictive")
        antenne = Site.objects.create(code="DEMO-ANT", nom="[DÉMO] Antenne régionale", adresse="Adresse fictive")
        dg = Service.objects.create(code="DEMO-DG", nom="[DÉMO] Direction générale", site=siege)
        services = {
            "DEMO-DG": dg,
            "DEMO-LOG": Service.objects.create(code="DEMO-LOG", nom="[DÉMO] Logistique", site=siege, parent=dg),
            "DEMO-RAF": Service.objects.create(
                code="DEMO-RAF", nom="[DÉMO] Administration et finances", site=siege, parent=dg
            ),
            "DEMO-PRG": Service.objects.create(code="DEMO-PRG", nom="[DÉMO] Programmes", site=antenne, parent=dg),
        }

        mot_de_passe = "Demo-" + secrets.token_urlsafe(9)
        for identifiant, matricule, nom, prenom, fonction, service, profils in COMPTES:
            agent = Agent.objects.create(
                matricule=matricule,
                nom=nom,
                prenom=prenom,
                fonction=fonction,
                service=services[service],
            )
            utilisateur = Utilisateur.objects.create_user(
                username=identifiant,
                password=mot_de_passe,
                agent=agent,
                first_name=prenom,
                last_name=nom,
            )
            utilisateur.groups.set(Group.objects.filter(name__in=profils))

        for code_service, matricule in CHEFS.items():
            service = services[code_service]
            service.chef = Agent.objects.get(matricule=matricule)
            service.save()

        circuit, _ = Circuit.objects.get_or_create(code="demo", defaults={"libelle": "[DÉMO] Circuit à deux niveaux"})
        EtapeCircuit.objects.get_or_create(
            circuit=circuit,
            ordre=1,
            defaults={"libelle": "Chef de service", "mode": EtapeCircuit.MODE_CHEF_SERVICE},
        )
        EtapeCircuit.objects.get_or_create(
            circuit=circuit,
            ordre=2,
            defaults={
                "libelle": "Responsable logistique",
                "mode": EtapeCircuit.MODE_PROFIL,
                "profil": Group.objects.get(name="responsable_logistique"),
            },
        )

        self.stdout.write(self.style.SUCCESS("Données de démonstration chargées."))
        self.stdout.write(f"Comptes : {', '.join(c[0] for c in COMPTES)}")
        self.stdout.write(f"Mot de passe commun (généré, affiché une seule fois) : {mot_de_passe}")
        self.stdout.write("Le compte demo.admin devra activer la double authentification à sa première connexion.")
