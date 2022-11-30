from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from firebase_admin import auth
from image.models import Thumbnail


class MokaProfile(models.Model):
    class PayoutStatus(models.TextChoices):
        HIGH_VALUE = "HIGH_VALUE"  # Founding creators!!!
        REGULAR = "REGULAR"

    firebase_uid = models.CharField(unique=True, null=False, max_length=128)

    thumbnail = models.ForeignKey(Thumbnail, null=True, on_delete=models.SET_NULL)
    display_name = models.CharField(
        max_length=200,
        null=True,
        unique=True,
        error_messages={
            "unique": "The username already exists",
        },
    )
    description = models.CharField(max_length=500, null=True)
    followings = models.ManyToManyField(
        "self",
        through="Follow",
        through_fields=("follower", "followee"),
        symmetrical=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    payout_status = models.CharField(
        choices=PayoutStatus.choices,
        null=False,
        default=PayoutStatus.REGULAR,
        max_length=50,
    )

    is_banned = models.BooleanField(default=False)

    def get_display_name(self):
        if self.display_name is not None:
            return self.display_name
        else:
            user = auth.get_user(self.firebase_uid)
            self.display_name = user.display_name
            self.save()
            return user.display_name

    def get_email(self):
        try:
            user = auth.get_user(self.firebase_uid)
            return user.email
        except Exception:
            return None

    def get_balance(self):
        try:
            return self.wallet.balance
        except ObjectDoesNotExist:
            return 0

    def get_platform_fee(self, usd_value):
        if usd_value <= 0:
            raise ValueError("Platform fee must be applied on nonzero positive values")
        if self.payout_status == MokaProfile.PayoutStatus.HIGH_VALUE:
            return round(usd_value * 0.05)
        else:
            return round(usd_value * 0.1)


class Follow(models.Model):
    # profile = MokaProfile.objects.get(id=1)
    # profile.following.all()
    # profile.followers.all()
    followee = models.ForeignKey(
        MokaProfile, related_name="followers", on_delete=models.CASCADE
    )
    follower = models.ForeignKey(
        MokaProfile, related_name="following", on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["followee", "follower"], name="unique_followers"
            )
        ]

    def __str__(self):
        f"{self.follower} follows {self.followee}"
