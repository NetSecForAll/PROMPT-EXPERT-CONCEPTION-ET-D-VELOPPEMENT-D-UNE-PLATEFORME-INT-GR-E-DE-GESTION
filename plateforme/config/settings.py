"""Réglages de la plateforme.

Toutes les valeurs sensibles ou propres à un environnement sont lues dans les
variables d'environnement (voir .env.exemple). Aucun secret n'est écrit ici.
"""

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(nom, defaut=None, obligatoire=False):
    valeur = os.environ.get(nom, defaut)
    if obligatoire and not valeur:
        raise ImproperlyConfigured(f"La variable d'environnement {nom} est obligatoire.")
    return valeur


def env_bool(nom, defaut=False):
    return str(env(nom, str(defaut))).lower() in ("1", "true", "oui", "yes")


# developpement | recette | production
ENVIRONNEMENT = env("ENVIRONNEMENT", "developpement")
EN_PRODUCTION = ENVIRONNEMENT == "production"

SECRET_KEY = env("DJANGO_SECRET_KEY", obligatoire=True)
DEBUG = env_bool("DJANGO_DEBUG", False) and not EN_PRODUCTION
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "auditlog",
    "django_q",
    "apps.noyau",
    "apps.journal",
    "apps.validation",
    "apps.alertes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "apps.noyau.middleware.DoubleAuthentificationMiddleware",
    "apps.noyau.middleware.EnTetesSecuriteMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    # Doit rester en dernier : intercepte les échecs de connexion.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.noyau.context_processors.plateforme",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "plateforme"),
        "USER": env("POSTGRES_USER", "plateforme"),
        "PASSWORD": env("POSTGRES_PASSWORD", obligatoire=True),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "ATOMIC_REQUESTS": True,
    }
}

AUTH_USER_MODEL = "noyau.Utilisateur"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "connexion"
LOGIN_REDIRECT_URL = "tableau_de_bord"
LOGOUT_REDIRECT_URL = "connexion"

# Verrouillage : 5 échecs consécutifs -> 15 minutes (cahier des charges §3.2).
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "registration/verrouille.html"
AXES_VERBOSE = False

# Sessions : expiration après 30 minutes d'inactivité.
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Profils pour lesquels la double authentification est obligatoire.
PROFILS_DOUBLE_AUTHENTIFICATION = ["admin_technique", "admin_fonctionnel"]
OTP_TOTP_ISSUER = env("OTP_EMETTEUR", "Plateforme de gestion")

LANGUAGE_CODE = "fr"
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path(env("STATIC_ROOT", BASE_DIR / "staticfiles"))
MEDIA_ROOT = Path(env("MEDIA_ROOT", BASE_DIR / "fichiers"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tâches planifiées (django-q2) : file d'attente stockée dans PostgreSQL, sans Redis.
Q_CLUSTER = {
    "name": "plateforme",
    "orm": "default",
    "workers": 2,
    "timeout": 600,
    "retry": 900,
    "catch_up": False,
}

# Alertes : délai après lequel une validation en attente est signalée.
ALERTE_VALIDATION_EN_ATTENTE_JOURS = int(env("ALERTE_VALIDATION_EN_ATTENTE_JOURS", "3"))

# Journal : un journal d'audit est conservé 5 ans par défaut.
JOURNAL_CONSERVATION_JOURS = int(env("JOURNAL_CONSERVATION_JOURS", str(5 * 365)))

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if EN_PRODUCTION:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Le préchargement HSTS dans les navigateurs est difficilement réversible :
    # il n'est pas activé par défaut.
    SILENCED_SYSTEM_CHECKS = ["security.W021"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
