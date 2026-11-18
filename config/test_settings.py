"""Settings for pytest: the same whatever the local .env says."""

import os
import tempfile

os.environ["DJANGO_SECRET_KEY"] = "test-only-not-a-secret"

from config.settings import *  # noqa: E402, F403

MEDIA_ROOT = tempfile.mkdtemp(prefix="keepee-test-media-")

# The tests check the English text; the Dutch ones say so with a language cookie.
LANGUAGE_CODE = "en"

# Fast: the tests log in hundreds of times.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# The manifest storage needs collectstatic, which tests don't run.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
