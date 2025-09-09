"""
Test settings for Django project.

This provides test-specific configurations that don't require
external services or environment variables.
"""

from pathlib import Path

from django.core.management.utils import get_random_secret_key

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent

# Test settings
DEBUG = True
SECRET_KEY = get_random_secret_key()

# Allow all hosts for testing
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS: list[str] = []

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "parliscope",
    "frontend",
    "ris",
    "fontawesomefree",
    "django_crontab",
    "health_check",
    "health_check.db",
    "health_check.contrib.migrations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "frontend.middleware.RestrictUserMiddleware",
]

ROOT_URLCONF = "frontend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "parliscope.wsgi.application"

# Internationalization
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_TZ = True
USE_I18N = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Test databases - use SQLite in-memory for both databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
    "ris": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

DATABASE_ROUTERS = ["frontend.databaserouter.DatabaseRouter"]

# Disable external service dependencies for tests
SOLR_HOST = "http://mock-solr:8983/solr"
SOLR_COLLECTION = "test_ris"
TIKA_HOST = "http://mock-tika:9998"
PDFACT_HOST = "http://mock-pdfact:80"
GOTENBERG_HOST = "http://mock-gotenberg:3000"
PREVIEW_HOST = "http://mock-preview:8000"

# Test document storage
DOCUMENT_STORE = "/tmp/test_filestore"
CACHE_DIR = "/tmp/test_cache"

# Allow all hosts for testing
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = []

# Disable cron jobs for tests
CRONJOBS: list[str] = []

# Speed up password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item: str) -> bool:
        return True

    def __getitem__(self, item: str) -> None:
        return None


MIGRATION_MODULES = DisableMigrations()
