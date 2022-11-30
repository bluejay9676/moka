"""
Contains the config for the library
"""

from django.conf import settings


class Config:
    """
    Configuration taken from Django's settings
    """

    @property
    def account_id(self):
        return settings.CLOUDFLARE_ACCOUNT_ID

    @property
    def api_token(self):
        return settings.CLOUDFLARE_IMAGES_API_TOKEN

    @property
    def account_hash(self):
        return settings.CLOUDFLARE_IMAGES_ACCOUNT_HASH

    @property
    def domain(self):
        return (
            settings.CLOUDFLARE_IMAGES_DOMAIN
            if hasattr(settings, "CLOUDFLARE_IMAGES_DOMAIN")
            else None
        )

    @property
    def variant(self):
        return (
            settings.CLOUDFLARE_IMAGES_VARIANT
            if hasattr(settings, "CLOUDFLARE_IMAGES_VARIANT")
            else "public"
        )
