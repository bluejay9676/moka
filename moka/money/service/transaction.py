"""
Logics regarding safely transfering balance from one wallet to another.

Unit is one cent (as per stripe)
One coin costs one cent
"""
import math

from django.db import transaction
from django.shortcuts import get_object_or_404
from episode.models import PurchaseEpisode
from moka_profile.models import MokaProfile
from money.models import Transaction, Wallet

# Never change these constants! As this subjects to messing with internal economy
CENTS_PER_COIN = 1
CENTS_PER_USD = 100


class WithdrawAmountExceedsBalance(Exception):
    pass


class NotEnoughBalance(Exception):
    pass


class NegativeAmount(Exception):
    pass


class OverMaximumAmount(Exception):
    pass


def remove_stored_connect_acct_id(connected_acct_id):
    with transaction.atomic():
        # Lock wallet
        wallet = Wallet.objects.select_for_update().get(
            stripe_connect_account=connected_acct_id,
        )
        wallet.stripe_connect_account = None
        wallet.save()


def deposit(owner_id, coin_amount, usd_value):
    with transaction.atomic():
        if coin_amount < 0 or usd_value < 0:
            raise NegativeAmount

        owner = get_object_or_404(
            MokaProfile.objects,
            id=owner_id,
        )
        # Lock wallet
        buyer_wallet_locked = Wallet.objects.select_for_update().get(
            owner=owner,
        )
        # Wallet object should always exist since this path is reachable from deposit-coin-session
        # Which creates wallet obj if it doesn't exist.
        buyer_wallet_locked.balance += coin_amount
        buyer_wallet_locked.usd_value += usd_value
        buyer_wallet_locked.save()

        Transaction.objects.create(
            type=Transaction.Type.DEPOSIT,
            sender=owner,
            recipient=owner,
            coin_amount=coin_amount,
            usd_value=usd_value,
        )


def add_balance_to_wallet(stripe_handler, stripe_session):
    if stripe_session["payment_status"] == "paid":
        (nominal, net,) = stripe_handler.retrieve_balance_transaction_nominal_and_net(
            stripe_session["payment_intent"]
        )
        deposit(
            owner_id=stripe_session["client_reference_id"],
            coin_amount=nominal,
            usd_value=net,
        )


def __transfer_coins(
    recipient,
    sender,
    amount,
):
    """
    This method must be called within transaction.atomic() context
    """
    if amount < 0:
        raise NegativeAmount
    if amount > 10000000:
        raise OverMaximumAmount

    sender_wallet_locked, _ = Wallet.objects.select_for_update().get_or_create(
        owner=sender
    )
    recipient_wallet_locked, _ = Wallet.objects.select_for_update().get_or_create(
        owner=recipient
    )
    # Check if buyer has enough balance
    if sender_wallet_locked.balance < amount:
        raise NotEnoughBalance

    # Subtract amount and corresponding usd_value based on the episode price from the buyer wallet
    # Add the same amount and usd_value to the owner wallet
    transfer_coins = amount
    transfer_usd_value = amount * sender_wallet_locked.usd_value_per_coin()

    sender_wallet_locked.balance -= transfer_coins
    sender_wallet_locked.usd_value -= transfer_usd_value
    recipient_wallet_locked.monthly_profit_balance += transfer_coins
    recipient_wallet_locked.monthly_profit_usd_value += transfer_usd_value

    sender_wallet_locked.save()
    recipient_wallet_locked.save()

    Transaction.objects.create(
        type=Transaction.Type.PURCHASE,
        sender=sender,
        recipient=recipient,
        coin_amount=transfer_coins,
        usd_value=transfer_usd_value,
    )


def send_tip(
    recipient,
    sender,
    amount,
):
    with transaction.atomic():
        __transfer_coins(recipient, sender, amount)


def purchase_episode(
    buyer,
    episode,
):
    with transaction.atomic():
        __transfer_coins(
            recipient=episode.series.owner, sender=buyer, amount=episode.price
        )
        # Once the successful, create purchase relationship.
        PurchaseEpisode.objects.create(
            episode=episode,
            profile=buyer,
        )


def move_monthly_balance_to_payout_balance():
    with transaction.atomic():
        wallets = Wallet.objects.select_for_update().all()
        bulk_update_wallets = []
        for wallet in wallets:
            if wallet.monthly_profit_balance > 0:
                wallet.payout_balance += wallet.monthly_profit_balance
                wallet.payout_usd_value += wallet.monthly_profit_usd_value
                wallet.monthly_profit_usd_value = 0
                wallet.monthly_profit_balance = 0
                bulk_update_wallets.append(wallet)
        Wallet.objects.bulk_update(
            bulk_update_wallets,
            [
                "payout_balance",
                "payout_usd_value",
                "monthly_profit_usd_value",
                "monthly_profit_balance",
            ],
        )


def payout(stripe_handler):
    payout_eligibile_wallets = (
        Wallet.objects.select_for_update()
        .filter(
            payout_balance__gte=300,
        )
        .exclude(
            stripe_connect_account__isnull=True,
        )
    )
    with transaction.atomic():
        for wallet in payout_eligibile_wallets:
            account = stripe_handler.get_account(wallet.stripe_connect_account)
            if not account["charges_enabled"]:
                continue  # Payout is disabled

            Transaction.objects.create(
                type=Transaction.Type.WITHDRAW,
                sender=wallet.owner,
                recipient=wallet.owner,
                coin_amount=wallet.payout_balance,
                usd_value=wallet.payout_usd_value,
            )

            platform_fee = wallet.owner.get_platform_fee(wallet.payout_usd_value)
            stripe_handler.create_transfer(
                usd_amount=math.floor(wallet.payout_usd_value - platform_fee),
                account_id=wallet.stripe_connect_account,
                metadata={
                    "coins": wallet.payout_balance,
                    "eligible_value": wallet.payout_usd_value,
                    "platform_fee": platform_fee,
                },
            )
            wallet.payout_balance = 0
            wallet.payout_usd_value = 0

        Wallet.objects.bulk_update(
            payout_eligibile_wallets,
            [
                "payout_balance",
                "payout_usd_value",
                "monthly_profit_usd_value",
                "monthly_profit_balance",
            ],
        )
