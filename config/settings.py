import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Application embarquee dans un executable PyInstaller : la base SQLite vit
# dans le dossier courant (a cote de l'exe), pas dans le bundle en lecture seule.
FROZEN = getattr(sys, "frozen", False)
DOSSIER_DONNEES = Path(os.getcwd()) if FROZEN else BASE_DIR

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-key-change-me-in-production"
    else:
        # Hebergement : cle efemere par demarrage si aucune cle fournie (les sessions
        # seront invalidees a chaque redemarrage ; definir DJANGO_SECRET_KEY en prod).
        import secrets as _secrets
        SECRET_KEY = _secrets.token_urlsafe(50)
        print("ATTENTION : DJANGO_SECRET_KEY non defini, cle efemere generee pour ce demarrage.")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
# Derriere un proxy/gateway HTTPS (hebergement) :
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "planning",
]

# X-Frame-Options : DENY par defaut (anti-clickjacking). Dans un Codespace, l'aperçu
# integre de VS Code charge l'app en iframe cross-origin -> ERR_BLOCKED_BY_RESPONSE ;
# le devcontainer definit X_FRAME_OPTIONS="" pour desactiver l'en-tete en demo.
# En production, laisser DENY (ou SAMEORIGIN) et ouvrir l'app dans un vrai onglet.
_X_FRAME_OPTIONS = os.environ.get("X_FRAME_OPTIONS", "DENY")
X_FRAME_OPTIONS = _X_FRAME_OPTIONS if _X_FRAME_OPTIONS else None

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
if X_FRAME_OPTIONS is not None:
    MIDDLEWARE.append("django.middleware.clickjacking.XFrameOptionsMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "planning.context_processors.navigation",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DOSSIER_DONNEES / "db.sqlite3",
    }
}

# Hebergement avec base geree (ex. Postgres managée Mistral fournie via DATABASE_URL) :
_DATABASE_URL = os.environ.get("DATABASE_URL")
if _DATABASE_URL:
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(_DATABASE_URL, conn_max_age=600)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = DOSSIER_DONNEES / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "planning_annee_mois_courant"
LOGOUT_REDIRECT_URL = "planning_annee_mois_courant"

# Le planning est lisible de partout, sans connexion (lecture seule).
# Mettre a "0" pour exiger au minimum le niveau Visionnage connecte.
PLANNING_PUBLIC_READ = os.environ.get("PLANNING_PUBLIC_READ", "1") == "1"

# Heures de reference d'un praticien a 100 % sur une annee.
HEURES_ANNUELLES_100 = 1747
