from django.db import models
from image.models import Thumbnail
from moka_profile.models import MokaProfile
from taggit.managers import TaggableManager


class Series(models.Model):
    class Meta:
        verbose_name_plural = "Series'"

    class SeriesStatus(models.TextChoices):
        PUBLIC = "PUBLIC"
        DRAFT = "DRAFT"
        REMOVED = "REMOVED"

    owner = models.ForeignKey(
        MokaProfile, null=False, on_delete=models.CASCADE, related_name="owning_series"
    )

    thumbnail = models.ForeignKey(Thumbnail, null=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=100, null=False)
    description = models.CharField(max_length=500, null=True)
    status = models.CharField(
        choices=SeriesStatus.choices,
        null=False,
        max_length=10,
    )

    # https://django-taggit.readthedocs.io/en/latest/getting_started.html#getting-started
    tags = TaggableManager()

    publish_date = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_banned = models.BooleanField(default=False)

    def get_tags(self):
        return list(self.tags.names())

    def is_owner(self, profile: MokaProfile):
        return self.owner.id == profile.id
