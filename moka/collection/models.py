from django.db import models
from moka_profile.models import MokaProfile
from series.models import Series


class AbstractCollection(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        MokaProfile, null=False, on_delete=models.CASCADE, related_name="%(class)ss"
    )
    private = models.BooleanField(default=False)

    series = models.ManyToManyField(Series, related_name="included_%(class)ss")
    followers = models.ManyToManyField(MokaProfile, related_name="following_%(class)ss")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Collection(AbstractCollection):
    """Curated by the owner"""

    pass


class FollowingCollection(AbstractCollection):
    """Series followed by the owner"""

    pass
