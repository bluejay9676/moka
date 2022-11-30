from django.apps import AppConfig


class ImageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "image"

    def ready(self):
        # pylint: disable=import-outside-toplevel
        import moka.image.signals.handlers  # noqa: F401
