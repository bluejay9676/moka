"""
Contains the config for the library
"""

from django.conf import settings


class Config:
    """
    Configuration taken from Django's settings
    """

    @property
    def signing_key(self):
        return settings.GC_CDN_SIGNING_KEY

    @property
    def signing_key_name(self):
        return settings.GC_CDN_SIGNING_KEY_NAME

    @property
    def bucket_name(self):
        return settings.GCS_BUCKET_NAME

    @property
    def cdn_hostname(self):
        return settings.GC_CDN_HOSTNAME
