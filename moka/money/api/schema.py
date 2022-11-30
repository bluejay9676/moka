import datetime
from typing import Optional

from money.gateway.stripe import StripeHandler
from money.models import Transaction, Wallet
from ninja import Schema

stripe_handler = StripeHandler()


class DepositCoinsInputSchema(Schema):
    current_path: str
    coins: int


class DepositCoinsOutputSchema(Schema):
    checkout_session_url: str


class CreateConnectAccountInputSchema(Schema):
    refresh_url: str
    return_url: str


class CreateConnectAccountOutputSchema(Schema):
    onboard_url: str


class PurchaseEpisodeInputSchema(Schema):
    episode_id: str


class TipInputSchema(Schema):
    profile_id: Optional[str]
    episode_id: Optional[str]
    amount: int


class WalletMetaDataOutputSchema(Schema):
    balance: int
    usd_value: float
    # Stripe account charges_enabled
    payout_enabled: bool

    creator_status: str
    stripe_account_email: Optional[str]

    monthly_profit_balance: int
    monthly_profit_usd_value: float

    payout_balance: int
    payout_usd_value: float

    @staticmethod
    def resolve_balance(obj: Wallet):
        return obj.balance

    @staticmethod
    def resolve_usd_value(obj: Wallet):
        return obj.usd_value

    @staticmethod
    def resolve_payout_enabled(obj: Wallet):
        if obj.stripe_connect_account:
            # If they already submitted the full information, please wait until Stripe approves of payout
            return stripe_handler.get_account(obj.stripe_connect_account)[
                "charges_enabled"
            ]
        else:
            return False

    @staticmethod
    def resolve_creator_status(obj: Wallet):
        return obj.owner.payout_status

    @staticmethod
    def resolve_stripe_account_email(obj: Wallet):
        if obj.stripe_connect_account:
            return stripe_handler.get_account(obj.stripe_connect_account)["email"]
        else:
            return None

    @staticmethod
    def resolve_monthly_profit_balance(obj: Wallet):
        return obj.monthly_profit_balance

    @staticmethod
    def resolve_monthly_profit_usd_value(obj: Wallet):
        return obj.monthly_profit_usd_value

    @staticmethod
    def resolve_payout_balance(obj: Wallet):
        return obj.payout_balance

    @staticmethod
    def resolve_payout_usd_value(obj: Wallet):
        return obj.payout_usd_value


class TransactionSchema(Schema):
    type: str
    coin_amount: int
    usd_value: float
    sender_id: int
    sender_display_name: str
    recipient_id: int
    recipient_display_name: str
    created_at: datetime.datetime

    @staticmethod
    def resolve_type(obj: Transaction):
        return obj.type

    @staticmethod
    def resolve_coin_amount(obj: Transaction):
        return obj.coin_amount

    @staticmethod
    def resolve_usd_value(obj: Transaction):
        return obj.usd_value

    @staticmethod
    def resolve_sender_id(obj: Transaction):
        return obj.sender.id

    @staticmethod
    def resolve_sender_display_name(obj: Transaction):
        return obj.sender.display_name

    @staticmethod
    def resolve_recipient_id(obj: Transaction):
        return obj.recipient.id

    @staticmethod
    def resolve_recipient_display_name(obj: Transaction):
        return obj.recipient.display_name

    @staticmethod
    def resolve_created_at(obj: Transaction):
        return obj.created_at


class RecentIncomeAmountSchema(Schema):
    amount: int
    usd_value: float
