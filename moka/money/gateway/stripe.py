import stripe
from django.conf import settings
from moka_profile.models import MokaProfile
from money.service.transaction import CENTS_PER_COIN


class BelowMinimumCoinPurchase(Exception):
    pass


class StripeHandler:
    def __init__(self):
        stripe.api_key = settings.STRIPE_API_KEY

    def create_coin_purchase_checkout_session(
        self,
        profile: MokaProfile,
        coins: int,
        success_url: str,
        cancel_url: str,
    ):
        """
        For local test,
        - Enter 4242 4242 4242 4242 as the card number
        - Enter any future date for card expiry
        - Enter any 3-digit number for CVV
        """
        if coins < 300:
            raise BelowMinimumCoinPurchase

        # https://www.patreon.com/pricing
        # https://support.patreon.com/hc/en-us/articles/360027674431-What-fees-can-I-expect-as-a-creator-
        return stripe.checkout.Session.create(
            customer_email=profile.get_email(),
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{coins} coins",
                            "description": f"{coins} coins.",
                        },
                        "tax_behavior": "exclusive",
                        "unit_amount": coins * CENTS_PER_COIN,
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            metadata={
                "coins": coins,
            },
            success_url=success_url,
            cancel_url=cancel_url,
            automatic_tax={"enabled": True},
            client_reference_id=profile.id,
        )

    def retrieve_balance_transaction_nominal_and_net(self, payment_intent_id):
        nominal, net = 0, 0
        pi = stripe.PaymentIntent.retrieve(payment_intent_id)
        for charge in pi["charges"]["data"]:
            btxn = stripe.BalanceTransaction.retrieve(
                charge["balance_transaction"],
            )
            nominal += btxn["amount"]
            net += btxn["net"]
        return nominal, net

    def create_connect_account(self, profile: MokaProfile):
        return stripe.Account.create(
            type="standard",
        )

    def create_account_onboarding(
        self,
        account_id,
        refresh_url,
        return_url,
    ):
        return stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type="account_onboarding",
        )

    def get_account(
        self,
        account_id,
    ):
        return stripe.Account.retrieve(
            id=account_id,
        )

    def create_transfer(
        self,
        usd_amount,
        account_id,
        metadata,
    ):
        return stripe.Transfer.create(
            amount=usd_amount,
            currency="usd",
            destination=account_id,
            metadata=metadata,
        )
