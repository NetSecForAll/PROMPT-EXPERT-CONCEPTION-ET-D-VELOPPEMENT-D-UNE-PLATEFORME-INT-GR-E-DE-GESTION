"""Installation complète de la plateforme en une seule commande.

    python installer.py          (terminal, depuis le dossier plateforme/)
    %run installer.py            (cellule Jupyter, carnet ouvert depuis plateforme/)

Étapes : dépendances Python → secrets → .env → utilisateur et base PostgreSQL →
tables → compte administrateur → données de démonstration (facultatif).

Tous les secrets et mots de passe utilisés sont affichés à la fin ET écrits dans
IDENTIFIANTS.txt. Ce fichier n'est jamais versionné (.gitignore) : le conserver
en lieu sûr, puis le supprimer du serveur.

Relancer le script ne change pas les secrets déjà écrits dans .env.
Variables facultatives :
    PG_SUPERUSER / PG_SUPERUSER_PASSWORD   compte « postgres » servant à créer la base
    ADMIN_IDENTIFIANT                      identifiant du compte administrateur (admin)
    SANS_DEMO=1                            ne pas charger les données de démonstration
"""

import getpass
import os
import secrets
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    DOSSIER = Path(__file__).resolve().parent
except NameError:  # code collé dans une cellule Jupyter
    DOSSIER = Path.cwd()

FICHIER_ENV = DOSSIER / ".env"
FICHIER_IDENTIFIANTS = DOSSIER / "IDENTIFIANTS.txt"


def etape(texte):
    print(f"\n=== {texte}")


def executer(*args, **kwargs):
    return subprocess.run([sys.executable, *args], cwd=DOSSIER, check=True, text=True, **kwargs)


def lire_env():
    valeurs = {}
    if FICHIER_ENV.exists():
        for ligne in FICHIER_ENV.read_text(encoding="utf-8").splitlines():
            if "=" in ligne and not ligne.lstrip().startswith("#"):
                cle, valeur = ligne.split("=", 1)
                valeurs[cle.strip()] = valeur.split(" #")[0].strip()
    return valeurs


def ecrire_env(valeurs):
    modele = (DOSSIER / ".env.exemple").read_text(encoding="utf-8").splitlines()
    lignes = []
    for ligne in modele:
        cle = ligne.split("=", 1)[0].strip()
        if "=" in ligne and not ligne.lstrip().startswith("#") and cle in valeurs:
            lignes.append(f"{cle}={valeurs[cle]}")
        else:
            lignes.append(ligne)
    FICHIER_ENV.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def creer_base(env):
    import psycopg
    from psycopg import sql

    super_utilisateur = os.environ.get("PG_SUPERUSER", "postgres")
    mdp_super = os.environ.get("PG_SUPERUSER_PASSWORD")
    if mdp_super is None:
        mdp_super = getpass.getpass(
            f"Mot de passe du compte PostgreSQL « {super_utilisateur} » (choisi à l'installation de PostgreSQL) : "
        )
    connexion = psycopg.connect(
        host=env["POSTGRES_HOST"],
        port=env["POSTGRES_PORT"],
        user=super_utilisateur,
        password=mdp_super or None,
        dbname="postgres",
        autocommit=True,
    )
    with connexion:
        utilisateur, base, mdp = env["POSTGRES_USER"], env["POSTGRES_DB"], env["POSTGRES_PASSWORD"]
        existe = connexion.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [utilisateur]).fetchone()
        ordre = "ALTER" if existe else "CREATE"
        connexion.execute(
            sql.SQL(ordre + " ROLE {} WITH LOGIN CREATEDB PASSWORD {}").format(
                sql.Identifier(utilisateur), sql.Literal(mdp)
            )
        )
        if not connexion.execute("SELECT 1 FROM pg_database WHERE datname = %s", [base]).fetchone():
            connexion.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(base), sql.Identifier(utilisateur))
            )
    return super_utilisateur, mdp_super


def main():
    os.chdir(DOSSIER)
    if not (DOSSIER / "manage.py").exists():
        sys.exit("Lancez ce script depuis le dossier plateforme/ (celui qui contient manage.py).")

    etape("1/6 Installation des dépendances Python (Django, psycopg…)")
    executer("-m", "pip", "install", "-q", "-r", "requirements.txt")

    etape("2/6 Secrets et fichier .env")
    env = lire_env()
    deja = bool(env)
    env.setdefault("ENVIRONNEMENT", "developpement")
    env.setdefault("DJANGO_DEBUG", "true")
    env.setdefault("POSTGRES_DB", "plateforme")
    env.setdefault("POSTGRES_USER", "plateforme")
    env.setdefault("POSTGRES_HOST", "localhost")
    env.setdefault("POSTGRES_PORT", "5432")
    if env.get("DJANGO_SECRET_KEY", "remplacer-par-une-longue-valeur-aleatoire").startswith("remplacer"):
        env["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(50)
    if env.get("POSTGRES_PASSWORD", "remplacer") == "remplacer":
        env["POSTGRES_PASSWORD"] = secrets.token_urlsafe(18)
    ecrire_env(env)
    print(".env " + ("complété (secrets existants conservés)" if deja else "créé"))

    etape("3/6 Utilisateur et base PostgreSQL")
    super_utilisateur, mdp_super = creer_base(env)
    print(f"Base « {env['POSTGRES_DB']} » prête pour l'utilisateur « {env['POSTGRES_USER']} »")

    etape("4/6 Création des tables")
    executer("manage.py", "migrate", "--noinput")

    etape("5/6 Compte administrateur")
    admin = os.environ.get("ADMIN_IDENTIFIANT", "admin")
    mdp_admin = "Adm-" + secrets.token_urlsafe(12)
    commande = (
        "import os\n"
        "from django.contrib.auth import get_user_model\n"
        "u, cree = get_user_model().objects.get_or_create(username=os.environ['ADMIN_IDENTIFIANT'])\n"
        "u.is_staff = u.is_superuser = u.is_active = True\n"
        "u.set_password(os.environ['ADMIN_MOT_DE_PASSE'])\n"
        "u.save()\n"
        "print('Compte créé' if cree else 'Compte existant : mot de passe réinitialisé')\n"
    )
    executer(
        "manage.py", "shell", "-c", commande,
        env={**os.environ, "ADMIN_IDENTIFIANT": admin, "ADMIN_MOT_DE_PASSE": mdp_admin},
    )

    etape("6/6 Données de démonstration")
    sortie_demo = ""
    if os.environ.get("SANS_DEMO") == "1":
        print("ignorées (SANS_DEMO=1)")
    else:
        resultat = subprocess.run(
            [sys.executable, "manage.py", "charger_demo"], cwd=DOSSIER, text=True, capture_output=True
        )
        sortie_demo = (resultat.stdout + resultat.stderr).strip()
        print(sortie_demo)

    rapport = f"""IDENTIFIANTS DE LA PLATEFORME — générés le {datetime.now():%d/%m/%Y %H:%M}
Fichier confidentiel : ne pas le versionner, ne pas l'envoyer par courriel.

--- Application (http://127.0.0.1:8000) -------------------------------------
Administrateur           : {admin}
Mot de passe             : {mdp_admin}
  (à la première connexion, activer la double authentification avec une
   application TOTP : FreeOTP, Aegis, Google/Microsoft Authenticator)

--- Données de démonstration --------------------------------------------------
{sortie_demo or "non chargées"}

--- PostgreSQL ----------------------------------------------------------------
Hôte / port              : {env['POSTGRES_HOST']}:{env['POSTGRES_PORT']}
Base                     : {env['POSTGRES_DB']}
Utilisateur              : {env['POSTGRES_USER']}
Mot de passe             : {env['POSTGRES_PASSWORD']}
Super-utilisateur        : {super_utilisateur}
Mot de passe             : {mdp_super or "(aucun / authentification locale)"}

--- Django (.env) ---------------------------------------------------------------
DJANGO_SECRET_KEY        : {env['DJANGO_SECRET_KEY']}

--- Lancement -----------------------------------------------------------------
python manage.py runserver
"""
    FICHIER_IDENTIFIANTS.write_text(rapport, encoding="utf-8")
    print("\n" + rapport)
    print(f"Ces informations sont enregistrées dans {FICHIER_IDENTIFIANTS}")


if __name__ == "__main__":
    main()
