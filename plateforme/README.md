# Plateforme intégrée de gestion — lot Socle

Application Django (Python 3.12+, PostgreSQL 16) qui sert de fondation aux modules
Parc automobile, Documents, Stocks, Projets et Rapports. Ce lot livre :

| Fonction | Où |
| --- | --- |
| Référentiels : sites, services (hiérarchie), agents, paramètres | `apps/noyau` |
| Comptes, 11 profils préconfigurés, règles anti-élévation de droits | `apps/noyau` (`profils.py`, `forms.py`) |
| Connexion, verrouillage après 5 échecs (15 min), session de 30 min | `config/settings.py`, django-axes |
| Double authentification TOTP obligatoire pour les administrateurs | `apps/noyau/middleware.py`, `views_auth.py` |
| Journal de sécurité et historique avant/après, non modifiables (déclencheur PostgreSQL) | `apps/journal` |
| Moteur de validation générique : circuits, étapes, seuils, délégations | `apps/validation` |
| Alertes : levée sans doublon, prise en compte, calcul nocturne | `apps/alertes` |
| Listes avec recherche, filtres, tri, pagination, export Excel | `apps/noyau/vues_generiques.py` |
| Interface responsive en français (Bootstrap 5 et HTMX servis localement) | `templates/`, `static/` |
| Données de démonstration identifiées, interdites en production | `manage.py charger_demo` |
| Sauvegarde et restauration vérifiée | `deploiement/scripts/` |

Les modules métier (parc, documents, stocks…) ne sont **pas encore** développés.

## Installation en une commande

Prérequis : Python 3.12+ et PostgreSQL 16 installé et démarré. Depuis ce dossier :

```bash
python installer.py      # ou, dans Jupyter : %run installer.py
python manage.py runserver
```

Le script installe les dépendances, génère la clé secrète et le mot de passe de la base,
écrit `.env`, crée l'utilisateur et la base PostgreSQL (il demande le mot de passe du
compte `postgres`), crée les tables, un compte `admin` et les données de démonstration.
**Tous les secrets et mots de passe sont affichés et enregistrés dans `IDENTIFIANTS.txt`**
(fichier exclu de Git : le conserver en lieu sûr). Le relancer conserve les secrets de
`.env` et génère un nouveau mot de passe `admin`.

## Installation pour le développement (étape par étape)

Prérequis : Python 3.12 ou plus récent, PostgreSQL 16.

```bash
# 1. Base de données (une fois)
sudo -u postgres psql -c "CREATE USER plateforme WITH PASSWORD 'choisir-un-mot-de-passe' CREATEDB;"
sudo -u postgres createdb -O plateforme plateforme

# 2. Environnement Python
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt

# 3. Configuration : copier puis compléter (clé secrète, mot de passe de la base)
cp .env.exemple .env
python -c "import secrets; print(secrets.token_urlsafe(50))"   # valeur pour DJANGO_SECRET_KEY

# 4. Création des tables et des profils
python manage.py migrate

# 5. Compte administrateur technique initial
python manage.py createsuperuser

# 6. (Facultatif) données de démonstration — affiche un mot de passe généré
python manage.py charger_demo

# 7. Lancement
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000. À la première connexion d'un administrateur, l'application
demande d'activer la double authentification avec une application TOTP (FreeOTP, Aegis,
Google Authenticator, Microsoft Authenticator…).

Tâches planifiées (calcul des alertes chaque nuit) :

```bash
python manage.py planifier_taches   # une fois : enregistre la tâche
python manage.py qcluster           # processus d'exécution, à laisser tourner
python manage.py calculer_alertes   # exécution manuelle immédiate
```

## Dépannage

**`ModuleNotFoundError: No module named 'django'`** — les dépendances ne sont pas installées
dans le Python utilisé. Activer l'environnement virtuel (`. .venv/bin/activate`, ou
`.venv\Scripts\activate` sous Windows) puis `pip install -r requirements.txt`.

**Avec Jupyter** : ne pas copier `settings.py`, `wsgi.py`… dans une cellule. Ce sont des
modules chargés par `manage.py` ; exécutés seuls, ils échouent (Django absent, puis
`__file__` non défini). Ouvrir plutôt `lancer_depuis_jupyter.ipynb` depuis ce dossier :
il installe les dépendances dans le noyau (`%pip install`) et lance les commandes
`manage.py`.

**`ImproperlyConfigured: La variable d'environnement … est obligatoire`** — le fichier
`.env` manque ou est incomplet : `cp .env.exemple .env` puis renseigner
`DJANGO_SECRET_KEY` et `POSTGRES_PASSWORD`.

## Tests et qualité

```bash
python -m pytest            # 74 tests ; nécessite PostgreSQL (droit CREATEDB pour la base de test)
ruff check .                # style et erreurs courantes
python manage.py check --deploy   # avec ENVIRONNEMENT=production
```

Les tests couvrent notamment : séparation des responsabilités (nul ne valide sa propre
demande, même par délégation), circuits à seuils, motifs obligatoires, verrouillage de
compte, double authentification, refus d'accès journalisés, immuabilité du journal,
modifications concurrentes, export limité aux données visibles, interdiction des données
de démonstration en production.

## Configuration du premier circuit de validation

Menu **Administration › Circuits de validation** (administrateur fonctionnel) :

1. Créer un circuit avec le code attendu par le module (ex. `mission`).
2. Ajouter les étapes dans l'ordre. Le mode « Chef de service du demandeur » utilise le
   chef déclaré sur la fiche Service ; si le demandeur est lui-même chef, la demande
   remonte au chef du service parent.
3. Un seuil (XOF) limite une étape aux demandes d'un montant supérieur ou égal.

Une demande ne peut pas avancer vers une étape sans valideur : l'erreur est signalée
au moment de la décision, rien n'est enregistré.

## Déploiement (un serveur)

Voir `deploiement/` : `docker-compose.yml` (PostgreSQL, application, tâches, Nginx),
`nginx.conf` (HTTPS, statiques, téléchargements protégés), scripts de sauvegarde.

```bash
cp .env.exemple .env      # ENVIRONNEMENT=production, DJANGO_DEBUG=false, POSTGRES_HOST=postgres, hôtes réels
docker compose -f deploiement/docker-compose.yml --env-file .env up -d --build
docker compose -f deploiement/docker-compose.yml exec web python manage.py migrate
docker compose -f deploiement/docker-compose.yml exec web python manage.py collectstatic --noinput
docker compose -f deploiement/docker-compose.yml exec web python manage.py createsuperuser
docker compose -f deploiement/docker-compose.yml exec web python manage.py planifier_taches
```

> Le fichier Compose a été validé (`docker compose config`) mais l'image n'a pas encore
> été construite ni exécutée : à vérifier sur le serveur de recette.

Mise à jour d'une version : sauvegarde → récupération du code → `migrate` →
`collectstatic` → redémarrage → contrôle de connexion. En cas d'échec, restauration de
la sauvegarde prise juste avant.

## Sauvegarde et restauration

```bash
deploiement/scripts/sauvegarde.sh                                   # base + fichiers + inventaire + empreintes
deploiement/scripts/restauration.sh sauvegardes/AAAAMMJJ-HHMMSS --oui            # remplace la base courante
deploiement/scripts/restauration.sh sauvegardes/AAAAMMJJ-HHMMSS essai_resto --oui # restaure dans une autre base
```

- `SAUVEGARDE_CLE=/chemin/fichier-phrase` chiffre les sauvegardes (AES-256) ; conserver
  cette phrase hors du serveur, sans elle la sauvegarde est irrécupérable.
- La restauration vérifie les empreintes SHA-256, puis compare l'effectif de chaque table
  à l'inventaire pris lors de la sauvegarde ; elle échoue si un seul écart apparaît.
- Copier chaque nuit le dossier `sauvegardes/` vers un support distinct du serveur.
- Tester une restauration complète dans une base séparée au moins une fois par mois.

Ces deux scripts ont été exécutés avec succès (avec et sans chiffrement) sur PostgreSQL 16.

## Limites connues de ce lot

- Pas encore de module métier : le moteur de validation et les alertes sont prêts à être
  utilisés par le module Parc automobile (prochain lot).
- La réinitialisation de mot de passe par courriel n'est pas active (aucun serveur de
  messagerie configuré) : l'administrateur réinitialise depuis la fiche du compte.
- Réinitialiser la double authentification d'un utilisateur ayant perdu son téléphone se
  fait pour l'instant par le superutilisateur dans `/admin-technique/` (appareils TOTP).
- La purge du journal au-delà de 5 ans n'est pas automatisée : le journal est protégé
  contre toute suppression par la base elle-même.
- Fuseau horaire par défaut : UTC, à régler dans `.env` (`TIME_ZONE`).
