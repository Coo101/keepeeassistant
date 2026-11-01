"""Settings for pytest: the same whatever the local .env says."""

import os

os.environ["DJANGO_SECRET_KEY"] = "test-only-not-a-secret"

from config.settings import *  # noqa: E402, F403

# The manifest storage needs collectstatic, which tests don't run.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
