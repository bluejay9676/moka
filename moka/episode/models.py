from django.core.cache import cache
from django.db import models
from image.models import Thumbnail
from moka_profile.models import MokaProfile
from series.models import Series


class Episode(models.Model):
    class EpisodeStatus(models.TextChoices):
        PUBLIC = "PUBLIC"
        PRE_RELEASE = "PRERELEASE"
        DRAFT = "DRAFT"
        REMOVED = "REMOVED"

    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name="episodes",
        related_query_name="episode",
    )
    thumbnail = models.ForeignKey(Thumbnail, null=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=100, null=False)
    status = models.CharField(
        choices=EpisodeStatus.choices,
        null=False,
        max_length=10,
    )

    likes = models.ManyToManyField(
        MokaProfile, through="LikeEpisode", related_name="liked_episodes"
    )
    views = models.PositiveBigIntegerField(default=0)

    is_premium = models.BooleanField(default=False)
    price = models.PositiveBigIntegerField(default=0)

    episode_number = models.PositiveIntegerField(null=False)
    publish_date = models.DateTimeField(null=True)
    release_scheduled_date = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    trend_score = models.FloatField(default=0)

    is_scroll_view = models.BooleanField(default=False)

    is_banned = models.BooleanField(default=False)

    is_nsfw = models.BooleanField(default=False)

    def get_likes(self):
        return self.likes.count()

    def is_liked_by(self, profile: MokaProfile):
        return self.likes.filter(id=profile.id).exists()

    def get_cache_key(self):
        return f"episode_{self.id}_views"

    def get_buffer_views(self):
        return cache.get_or_set(
            key=self.get_cache_key(),
            default=0,
            timeout=None,
        )

    def get_views(self):
        return self.views + self.get_buffer_views()

    def incr_view(self):
        try:
            cache.incr(self.get_cache_key())
        except ValueError:
            cache.set(
                key=self.get_cache_key(),
                value=1,
                timeout=None,  # Don't stale the cache
            )

    def clear_cached_views(self):
        cache.set(
            key=self.get_cache_key(),
            value=0,
            timeout=None,
        )

    def delete_cached_views(self):
        cache.delete(self.get_cache_key())


class LikeEpisode(models.Model):
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)
    profile = models.ForeignKey(MokaProfile, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)


class PurchaseEpisode(models.Model):
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE)
    profile = models.ForeignKey(MokaProfile, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
