from __future__ import division

from django.db import models
from moka_profile.models import MokaProfile


class Wallet(models.Model):
    owner = models.OneToOneField(
        MokaProfile,
        on_delete=models.CASCADE,
        related_name="wallet",
        null=True,
    )
    # Number of coins
    balance = models.PositiveBigIntegerField(default=0)
    # Actual USD value corresponding to the coins owned
    usd_value = models.FloatField(default=0)

    stripe_connect_account = models.CharField(max_length=500, null=True)

    # Monthly profit received
    monthly_profit_balance = models.PositiveBigIntegerField(default=0)
    monthly_profit_usd_value = models.FloatField(default=0)

    # Every 1st day of the month, monthly_profit_* will be moved over to
    # payout_*. Then on 8th of the month, we will transfer USD value
    # to connected stripe account (if the connect account is setup).
    payout_balance = models.PositiveBigIntegerField(default=0)
    payout_usd_value = models.FloatField(default=0)

    def usd_value_per_coin(self):
        return self.usd_value / self.balance


class Transaction(models.Model):
    class Type(models.TextChoices):
        WITHDRAW = "WITHDRAW"
        DEPOSIT = "DEPOSIT"
        PURCHASE = "PURCHASE"

    type = models.CharField(
        choices=Type.choices,
        null=False,
        max_length=50,
    )

    recipient = models.ForeignKey(
        MokaProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="receiving_transactions",
    )
    sender = models.ForeignKey(
        MokaProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sending_transactions",
    )

    coin_amount = models.PositiveBigIntegerField(null=False)
    usd_value = models.FloatField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)
