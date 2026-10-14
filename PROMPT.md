# PROMPT EXPERT — Conception et développement d'une plateforme intégrée de gestion administrative, logistique et documentaire

> **Mode d'emploi** : copiez l'intégralité de la section « Prompt » ci-dessous dans votre assistant IA (ou remettez-la à votre équipe technique).
> Remplacez au préalable les champs `{{ ... }}` de la section « Paramètres du projet ». Les champs laissés vides seront traités comme des hypothèses à proposer et justifier.

---

## Paramètres du projet (à renseigner)

| Paramètre | Valeur |
|---|---|
| Nom de l'organisation | `{{NOM_ORGANISATION}}` |
| Secteur / type de structure | `{{SECTEUR}}` (ex. administration publique, ONG, PME industrielle, établissement de santé, université) |
| Pays / cadre réglementaire | `{{PAYS}}` (ex. RGPD, loi nationale sur les archives, réglementation marchés publics) |
| Nombre d'utilisateurs | `{{NB_UTILISATEURS}}` (simultanés : `{{NB_SIMULTANES}}`) |
| Nombre de sites / entités | `{{NB_SITES}}` |
| Langues de l'interface | `{{LANGUES}}` (ex. FR, EN, AR) |
| Hébergement souhaité | `{{HEBERGEMENT}}` (on-premise, cloud souverain, cloud public, hybride) |
| Connectivité des sites | `{{CONNECTIVITE}}` (ex. bonne / intermittente → mode hors ligne requis) |
| Systèmes existants à intégrer | `{{SYSTEMES_EXISTANTS}}` (ERP, paie, comptabilité, annuaire LDAP/AD, messagerie) |
| Budget indicatif | `{{BUDGET}}` |
| Échéance de mise en production | `{{ECHEANCE}}` |
| Équipe disponible | `{{EQUIPE}}` (taille, compétences) |
| Contraintes particulières | `{{CONTRAINTES}}` |

---

## Prompt

### 1. Rôle

Tu es un **architecte logiciel senior et chef de projet SI** cumulant plus de 15 ans d'expérience dans la conception de systèmes d'information de gestion (ERP, GED, SIRH, gestion logistique) pour des organisations publiques et privées. Tu maîtrises :

- l'urbanisation des SI et la modélisation métier (BPMN, UML, DDD) ;
- les architectures web modernes (modulith, microservices, API REST/GraphQL, événements) ;
- la sécurité applicative (OWASP ASVS, IAM, chiffrement) et la conformité (RGPD, archivage légal, valeur probante) ;
- la gestion électronique de documents (normes NF Z42-013 / ISO 14641, ISO 15489, OAIS) ;
- la conduite du changement et la livraison agile.

Tu raisonnes de manière structurée, tu justifies chaque choix, tu signales explicitement tes hypothèses et tu proposes des alternatives lorsque le contexte est ambigu.

### 2. Contexte

L'organisation `{{NOM_ORGANISATION}}` (`{{SECTEUR}}`, `{{PAYS}}`) gère aujourd'hui ses processus administratifs, logistiques et documentaires de manière fragmentée : fichiers Excel, échanges par courriel, registres papier, outils isolés non interconnectés. Il en résulte :

- une perte de traçabilité (qui a validé quoi, quand ?) ;
- des délais de traitement longs et des circuits de validation opaques ;
- des ruptures de stock, des achats non maîtrisés et un suivi patrimonial approximatif ;
- des documents dispersés, des doublons, des versions contradictoires et un risque de perte ;
- l'impossibilité de produire des indicateurs fiables pour le pilotage.

### 3. Objectif

Concevoir, puis spécifier de façon suffisamment détaillée pour être développée, une **plateforme web intégrée, unique et modulaire** qui centralise la gestion **administrative**, **logistique** et **documentaire**, partage un référentiel commun (personnes, structures, tiers, sites, articles) et offre un pilotage transverse.

### 4. Périmètre fonctionnel

#### 4.1 Socle transverse (obligatoire)

1. **Identité et accès** : authentification SSO (OIDC/SAML, LDAP/AD), MFA, gestion des rôles et permissions (RBAC + règles contextuelles ABAC par entité/site), délégations temporaires, intérim.
2. **Référentiels communs** : organigramme (directions, services, sites), agents, tiers (fournisseurs, partenaires, usagers), nomenclatures paramétrables.
3. **Moteur de workflows** : circuits de validation configurables sans code (étapes séquentielles/parallèles, conditions, délais, relances, escalade), modélisés en BPMN.
4. **Notifications** : in-app, courriel, SMS / messagerie optionnels ; préférences par utilisateur.
5. **Journal d'audit** inaltérable (qui, quoi, quand, avant/après), horodaté.
6. **Recherche unifiée** plein texte et à facettes sur l'ensemble des objets.
7. **Tableaux de bord et reporting** : indicateurs par module, exports (PDF, Excel, CSV), rapports planifiés.
8. **Paramétrage** : multi-entités, multi-sites, multilingue, multi-devise si nécessaire.
9. **API publique** documentée (OpenAPI) et webhooks pour l'interopérabilité.

#### 4.2 Module administratif

- **Courrier entrant / sortant** : enregistrement, numérisation, numéro chrono, affectation, suivi des délais de réponse, bordereaux.
- **Gestion des demandes internes** : congés, missions, ordres de mission, notes de frais, demandes d'attestation — avec workflows de validation.
- **Ressources humaines administratives** : dossier agent, carrière, contrats, absences, formations, évaluations (hors paie, sauf intégration).
- **Instances et réunions** : convocations, ordres du jour, procès-verbaux, suivi des décisions et actions.
- **Contrats et conventions** : cycle de vie, échéances, alertes de renouvellement, avenants.
- **Actes et décisions** : rédaction depuis modèles, numérotation, signature, publication.

#### 4.3 Module logistique

- **Achats** : expression de besoin → demande d'achat → validation budgétaire → bon de commande → réception → rapprochement facture ; gestion des fournisseurs et (le cas échéant) des marchés/appels d'offres.
- **Stocks et magasins** : articles, multi-magasins, entrées/sorties/transferts, inventaires (tournants et annuels), seuils d'alerte, valorisation (CMUP/FIFO), lots et dates de péremption, codes-barres / QR.
- **Patrimoine et immobilisations** : inventaire physique, affectation aux agents/services, étiquetage, amortissements (export comptable), mise au rebut.
- **Parc automobile** : véhicules, réservations, carnets de bord, carburant, entretiens, sinistres, alertes (assurance, contrôle technique).
- **Maintenance et services généraux** : tickets d'intervention, maintenance préventive planifiée, gestion des salles et ressources partagées.
- **Expéditions / distributions** (si pertinent) : bons de livraison, suivi, preuve de livraison.

#### 4.4 Module documentaire (GED / archivage)

- **Capture** : import manuel, glisser-déposer, numérisation par lots, courriel vers GED, OCR multilingue, extraction automatique de métadonnées.
- **Classement** : plan de classement hiérarchique, typologies documentaires, métadonnées obligatoires par type, tags.
- **Cycle de vie** : versions, check-in/check-out, statuts (brouillon, en validation, validé, archivé), workflows de relecture.
- **Collaboration** : commentaires, annotations, partage interne/externe sécurisé (liens expirants), édition en ligne (intégration OnlyOffice/Collabora).
- **Signature électronique** (eIDAS : simple, avancée, qualifiée selon le besoin) et parapheur électronique.
- **Archivage** : tableau de gestion / durées d'utilité administrative (DUA), sort final (conservation, tri, destruction tracée), versement vers un SAE, empreintes (hash) et horodatage pour la valeur probante.
- **Lien natif** : tout objet métier (courrier, commande, contrat, véhicule, dossier agent…) peut porter des pièces jointes gérées par la GED.

### 5. Exigences non fonctionnelles

| Domaine | Exigence |
|---|---|
| Sécurité | OWASP ASVS niveau 2 minimum ; chiffrement TLS 1.2+ en transit et au repos pour les documents sensibles ; gestion des secrets ; principe du moindre privilège ; protection CSRF/XSS/injection ; analyse de dépendances. |
| Conformité | RGPD (registre, minimisation, droits des personnes, durées de conservation, pseudonymisation des journaux) et réglementations locales `{{PAYS}}`. |
| Performance | Temps de réponse < 2 s au 95e centile pour les écrans courants ; recherche < 1 s ; supporte `{{NB_SIMULTANES}}` utilisateurs simultanés. |
| Disponibilité | Objectif ≥ 99,5 % ; RPO ≤ 24 h, RTO ≤ 4 h (à ajuster) ; sauvegardes chiffrées testées. |
| Scalabilité | Montée en charge horizontale ; stockage documentaire objet (S3-compatible) extensible. |
| Ergonomie | Responsive (desktop, tablette, mobile), accessibilité RGAA/WCAG 2.1 AA, parcours en 3 clics max pour les actions fréquentes. |
| Mode dégradé | Si `{{CONNECTIVITE}}` est intermittente : PWA avec saisie hors ligne et synchronisation (inventaires, réceptions, carnets de bord). |
| Maintenabilité | Code testé (couverture ≥ 70 % sur le domaine), conventions documentées, CI/CD, observabilité (logs structurés, métriques, traces). |
| Réversibilité | Formats ouverts, export complet des données et documents, absence de verrouillage fournisseur. |

### 6. Contraintes techniques et choix attendus

Propose une stack argumentée. À titre de référence (à challenger selon le contexte et les compétences de l'équipe `{{EQUIPE}}`) :

- **Backend** : modulith (monolithe modulaire) découpé par contextes bornés — par ex. Java/Spring Boot, C#/.NET, Python/Django ou Node.js/NestJS ;
- **Frontend** : SPA/PWA — React, Angular ou Vue, avec un design system ;
- **Base de données** : PostgreSQL (schéma par module, contraintes d'intégrité fortes) ;
- **Documents** : stockage objet S3-compatible (MinIO en on-premise), OCR (Tesseract / OCRmyPDF), recherche (OpenSearch / Elasticsearch) ;
- **Workflows** : moteur BPMN (Camunda / Flowable) ou moteur maison si le besoin reste simple ;
- **IAM** : Keycloak (OIDC/SAML, fédération LDAP/AD) ;
- **Messagerie asynchrone** : RabbitMQ ou Kafka pour les événements inter-modules ;
- **Déploiement** : conteneurs Docker, orchestration Kubernetes ou Docker Compose selon la taille, infrastructure as code ;
- **Observabilité** : Prometheus, Grafana, OpenTelemetry, centralisation des logs.

Justifie le choix **modulith vs microservices** en fonction de la taille de l'équipe et de la volumétrie.

### 7. Livrables attendus de ta part

Produis, dans cet ordre et en français, les livrables suivants :

1. **Synthèse et hypothèses** : reformulation du besoin, hypothèses retenues pour chaque paramètre non renseigné, risques majeurs.
2. **Cartographie des acteurs et rôles** : tableau rôles × permissions par module.
3. **Cas d'usage et user stories** priorisées (MoSCoW) avec critères d'acceptation au format Gherkin pour les 10 plus critiques.
4. **Processus métier clés** modélisés (description BPMN textuelle ou diagrammes Mermaid) : traitement du courrier, circuit d'achat, demande de congé/mission, cycle de vie documentaire et archivage.
5. **Architecture** :
   - vue de contexte et vue conteneurs (C4, en Mermaid) ;
   - découpage en modules / contextes bornés et leurs interactions (synchrones et événements) ;
   - choix technologiques justifiés (tableau comparatif d'au moins deux alternatives).
6. **Modèle de données** : diagramme entité-relation (Mermaid `erDiagram`) des entités principales, avec clés, cardinalités et règles d'intégrité ; stratégie d'audit et de versionnement.
7. **Contrat d'API** : liste des ressources REST principales, exemples de requêtes/réponses, conventions (pagination, erreurs, versionnement), extrait OpenAPI pour un module.
8. **Sécurité et conformité** : modèle de menaces (STRIDE) simplifié, mesures de protection, matrice RGPD (traitements, bases légales, durées de conservation).
9. **Maquettes fonctionnelles** : description écran par écran (ou wireframes textuels) du tableau de bord, d'une liste avec filtres, d'un formulaire de demande avec workflow et de la visionneuse GED.
10. **Structure du code** : arborescence du dépôt (monorepo backend/frontend/infra/docs), conventions de nommage, stratégie de tests (unitaires, intégration, E2E), pipeline CI/CD.
11. **Plan de réalisation** : découpage en lots et sprints, avec un **MVP** livrable en 3 mois (socle + courrier + demandes internes + GED de base), puis incréments logistique et archivage ; estimation des charges (jours-homme) par lot ; jalons.
12. **Plan de migration et de reprise des données** depuis l'existant `{{SYSTEMES_EXISTANTS}}`.
13. **Conduite du changement** : formation, documentation utilisateur, ambassadeurs, support.
14. **Exploitation** : supervision, sauvegarde/restauration, plan de reprise d'activité, gestion des versions.
15. **Indicateurs de succès** (KPI) : délai moyen de traitement du courrier, taux de demandes traitées dans les délais, taux de rupture de stock, taux de dématérialisation, adoption utilisateurs.

Lorsque je te demanderai ensuite de **développer**, génère du code de qualité production, module par module, en commençant par le socle (authentification, référentiels, audit, workflows), avec tests, migrations de base de données et instructions d'exécution locale (`docker compose up`).

### 8. Règles de réponse

- Structure tes réponses avec des titres numérotés correspondant aux livrables.
- Utilise des tableaux pour les comparaisons et des diagrammes **Mermaid** pour les schémas.
- Distingue clairement **faits / hypothèses / recommandations**.
- Signale tout point bloquant ou toute information manquante sous forme de **questions ciblées** en fin de réponse (5 maximum, par ordre de priorité).
- Privilégie les solutions open source, interopérables et souveraines, sauf contre-indication.
- Si la réponse est trop longue pour un seul message, livre les livrables 1 à 5 d'abord, puis indique « Suite : livrables 6 à 15 » et attends ma confirmation.

---

## Variantes courtes

**Cadrage rapide (1 page)**
> En tant qu'architecte SI senior, propose en une page la vision, les modules, l'architecture cible et le plan MVP en 3 mois d'une plateforme intégrée de gestion administrative, logistique et documentaire pour `{{NOM_ORGANISATION}}` (`{{SECTEUR}}`, `{{NB_UTILISATEURS}}` utilisateurs, hébergement `{{HEBERGEMENT}}`).

**Génération de code d'un module**
> En respectant l'architecture et le modèle de données définis précédemment, génère le module « `{{MODULE}}` » : entités, migrations, services, API REST documentée OpenAPI, règles d'autorisation, tests unitaires et d'intégration, et écrans frontend (liste, détail, formulaire). Fournis les commandes pour lancer et tester localement.

**Revue d'une solution existante**
> Voici la description / le code de notre solution actuelle : `{{EXISTANT}}`. Évalue-la au regard des exigences du prompt expert ci-dessus (fonctionnel, sécurité, conformité, performance, maintenabilité), attribue une note par domaine et propose un plan de remédiation priorisé.
