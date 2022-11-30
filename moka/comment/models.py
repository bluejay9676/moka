from django.db import models
from episode.models import Episode
from moka_profile.models import MokaProfile


class Comment(models.Model):
    commenter = models.ForeignKey(
        MokaProfile,
        on_delete=models.CASCADE,
        related_name="comments",
        related_query_name="comment",
    )

    episode = models.ForeignKey(
        Episode,
        on_delete=models.CASCADE,
        related_name="comments",
        related_query_name="comment",
    )

    parent = models.ForeignKey(
        "self", null=True, on_delete=models.CASCADE, related_name="replies"
    )

    content = models.CharField(max_length=200)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LikeComment(models.Model):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="likes",
        related_query_name="like",
    )
    liker = models.ForeignKey(
        MokaProfile,
        on_delete=models.CASCADE,
        related_name="liked_comments",
        related_query_name="liked_comment",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["comment", "liker"], name="unique_comment_liker"
            )
        ]
