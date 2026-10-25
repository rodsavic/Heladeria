import os

os.environ.setdefault('DJANGO_SECRET_KEY', 'clave-solo-para-tests')
os.environ.setdefault('DATABASE_URL', 'sqlite://:memory:')

from .settings import *  # noqa

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
SECURE_SSL_REDIRECT = False
# El manifest solo existe tras collectstatic; en tests se usa el storage simple
STORAGES = {
    **STORAGES,
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
