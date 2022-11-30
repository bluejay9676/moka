from __future__ import division

import math
from unittest import mock

import django.test
from django.test import Client
from episode.factory import EpisodeFactory
from episode.models import Episode, PurchaseEpisode
from moka_profile.factory import MokaProfileFactory
from moka_profile.models import MokaProfile
from money.factory import WalletFactory
from money.gateway.stripe import StripeHandler
from money.models import Wallet
from money.service.transaction import (
    add_balance_to_wallet,
    move_monthly_balance_to_payout_balance,
    payout,
)

from .test_data import (
    BALANCE_TRANSACTION,
    PAID_SESSION,
    PAYMENT_INTENT,
    PAYOUT_DISABLED_ACCT,
    PAYOUT_ENABLED_ACCT,
    UNPAID_SESSION,
)


class TestDepositCoinSession(django.test.TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_coin_purchase_checkout_session_invalid_coins(self):
        profile = MokaProfileFactory()
        session = UNPAID_SESSION
        session["client_reference_id"] = profile.id
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ), mock.patch(
            "stripe.checkout.Session.create",
            return_value=session,
        ):
            response = self.client.post(
                path=f"/v1/money/deposit-coin-session",
                data={
                    "current_path": "hello.com",
                    "coins": 100,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

    def test_create_wallet_if_not_exist(self):
        profile = MokaProfileFactory()
        session = UNPAID_SESSION
        session["client_reference_id"] = profile.id
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ), mock.patch(
            "stripe.checkout.Session.create",
            return_value=session,
        ):
            with self.assertRaises(MokaProfile.wallet.RelatedObjectDoesNotExist):
                profile.wallet
            response = self.client.post(
                path=f"/v1/money/deposit-coin-session",
                data={
                    "current_path": "hello.com",
                    "coins": 100,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertIsNotNone(profile.wallet)

    def test_create_coin_purchase_checkout_session(self):
        profile = MokaProfileFactory()
        session = UNPAID_SESSION
        session["client_reference_id"] = profile.id
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ), mock.patch(
            "stripe.checkout.Session.create",
            return_value=session,
        ) as mock_session_create:
            response = self.client.post(
                path=f"/v1/money/deposit-coin-session",
                data={
                    "current_path": "hello.com",
                    "coins": 1000,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["checkout_session_url"], session["url"])
            mock_session_create.assert_called_with(
                customer_email=None,
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": "1000 coins",
                                "description": "1000 coins.",
                            },
                            "tax_behavior": "exclusive",
                            "unit_amount": 1000,
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                metadata={"coins": 1000},
                success_url="hello.com",
                cancel_url="hello.com",
                automatic_tax={"enabled": True},
                client_reference_id=profile.id,
            )
            # Balance not added yet
            self.assertEqual(profile.wallet.balance, 0)


class TestWebhook(django.test.TransactionTestCase):
    def setUp(self):
        self.client = Client()

    def test_checkout_complete_not_paid(self):
        profile: MokaProfile = MokaProfileFactory()
        Wallet.objects.create(owner=profile)
        session = UNPAID_SESSION
        session["client_reference_id"] = profile.id

        self.assertEqual(profile.wallet.balance, 0)
        self.assertEqual(profile.wallet.usd_value, 0)

        add_balance_to_wallet(
            stripe_handler=StripeHandler(),
            stripe_session=session,
        )
        # Nothing happens
        profile.refresh_from_db()
        self.assertEqual(profile.wallet.balance, 0)
        self.assertEqual(profile.wallet.usd_value, 0)

    def test_checkout_complete_paid(self):
        profile: MokaProfile = MokaProfileFactory()
        Wallet.objects.create(owner=profile)
        session = PAID_SESSION
        session["client_reference_id"] = profile.id

        with mock.patch(
            "stripe.PaymentIntent.retrieve",
            return_value=PAYMENT_INTENT,
        ), mock.patch(
            "stripe.BalanceTransaction.retrieve",
            return_value=BALANCE_TRANSACTION,
        ):
            self.assertEqual(profile.wallet.balance, 0)
            self.assertEqual(profile.wallet.usd_value, 0)

            add_balance_to_wallet(
                stripe_handler=StripeHandler(), stripe_session=session
            )
            profile.refresh_from_db()
            self.assertEqual(profile.wallet.balance, BALANCE_TRANSACTION["amount"])
            self.assertEqual(profile.wallet.usd_value, BALANCE_TRANSACTION["net"])

    def test_checkout_complete_previous_balance(self):
        profile: MokaProfile = MokaProfileFactory()
        Wallet.objects.create(owner=profile, balance=100, usd_value=55)
        session = PAID_SESSION
        session["client_reference_id"] = profile.id

        with mock.patch(
            "stripe.PaymentIntent.retrieve",
            return_value=PAYMENT_INTENT,
        ), mock.patch(
            "stripe.BalanceTransaction.retrieve",
            return_value=BALANCE_TRANSACTION,
        ):
            add_balance_to_wallet(
                stripe_handler=StripeHandler(), stripe_session=session
            )

            profile.refresh_from_db()
            self.assertEqual(
                profile.wallet.balance, 100 + BALANCE_TRANSACTION["amount"]
            )
            self.assertEqual(profile.wallet.usd_value, 55 + BALANCE_TRANSACTION["net"])


class TestPayoutAccountCreate(django.test.TransactionTestCase):
    def test_connect_account_already_exists(self):
        profile = MokaProfileFactory()
        Wallet.objects.create(
            owner=profile, stripe_connect_account=PAYOUT_DISABLED_ACCT["id"]
        )
        with mock.patch(
            "stripe.Account.create",
            return_value=PAYOUT_DISABLED_ACCT,
        ) as mock_acct_create, mock.patch(
            "stripe.AccountLink.create",
            return_value={"url": "test.com"},
        ) as mock_acct_link_create, mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ):
            response = self.client.post(
                path=f"/v1/money/payout-account-create",
                data={
                    "refresh_url": "hello.com",
                    "return_url": "hello.com",
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["onboard_url"], "test.com")
            mock_acct_create.assert_not_called()
            mock_acct_link_create.assert_called()

    def test_connect_account_new(self):
        profile = MokaProfileFactory()
        with mock.patch(
            "stripe.Account.create",
            return_value=PAYOUT_DISABLED_ACCT,
        ) as mock_acct_create, mock.patch(
            "stripe.AccountLink.create",
            return_value={"url": "test.com"},
        ) as mock_acct_link_create, mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ):
            response = self.client.post(
                path=f"/v1/money/payout-account-create",
                data={
                    "refresh_url": "hello.com",
                    "return_url": "hello.com",
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["onboard_url"], "test.com")
            mock_acct_create.assert_called()
            mock_acct_link_create.assert_called()


class TestPurchaseEpisodes(django.test.TestCase):
    def test_not_enough_balance(self):
        buyer = MokaProfileFactory()
        Wallet.objects.create(owner=buyer, usd_value=1, balance=10)
        episode = EpisodeFactory(
            status=Episode.EpisodeStatus.PRE_RELEASE,
            price=100,
        )
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=buyer,
        ):
            response = self.client.post(
                path=f"/v1/money/purchase-episode",
                data={
                    "episode_id": episode.id,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["message"], "Not enough balance")

    def test_not_eligible_episode(self):
        buyer = MokaProfileFactory()
        Wallet.objects.create(owner=buyer, usd_value=999, balance=1000)
        draft_episode = EpisodeFactory(
            status=Episode.EpisodeStatus.DRAFT,
            price=100,
        )
        price_not_set_episode = EpisodeFactory(
            status=Episode.EpisodeStatus.PRE_RELEASE,
            price=0,
        )
        regular_public = EpisodeFactory(
            status=Episode.EpisodeStatus.PUBLIC,
        )
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=buyer,
        ):
            response = self.client.post(
                path=f"/v1/money/purchase-episode",
                data={
                    "episode_id": draft_episode.id,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.json()["message"], "Episode is not eligible for a purchase"
            )

            response = self.client.post(
                path=f"/v1/money/purchase-episode",
                data={
                    "episode_id": price_not_set_episode.id,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.json()["message"], "Episode is not eligible for a purchase"
            )

            response = self.client.post(
                path=f"/v1/money/purchase-episode",
                data={
                    "episode_id": regular_public.id,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.json()["message"], "Episode is not eligible for a purchase"
            )

    def test_success(self):
        # Check balance and usd_value change
        # Check purchase connection made
        buyer = MokaProfileFactory()
        buyer_wallet = Wallet.objects.create(owner=buyer, usd_value=999, balance=1000)
        episode = EpisodeFactory(
            status=Episode.EpisodeStatus.PRE_RELEASE,
            price=100,
        )
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=buyer,
        ):
            response = self.client.post(
                path=f"/v1/money/purchase-episode",
                data={
                    "episode_id": episode.id,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

            buyer_wallet.refresh_from_db()
            seller_wallet = episode.series.owner.wallet
            self.assertEqual(buyer_wallet.usd_value, 899.1)
            self.assertEqual(buyer_wallet.balance, 900)
            self.assertEqual(seller_wallet.monthly_profit_usd_value, 99.9)
            self.assertEqual(seller_wallet.monthly_profit_balance, 100)
            self.assertEqual(seller_wallet.usd_value, 0)
            self.assertEqual(seller_wallet.balance, 0)

            self.assertTrue(
                PurchaseEpisode.objects.filter(
                    episode=episode,
                    profile=buyer,
                ).exists()
            )


class TestWallet(django.test.TestCase):
    def test_new_wallet(self):
        profile = MokaProfileFactory()

        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ):
            response = self.client.get(
                path=f"/v1/money/wallet",
                content_type="application/json",
            ).json()
            self.assertEqual(response["balance"], 0)
            self.assertEqual(response["usd_value"], 0)
            self.assertEqual(response["payout_enabled"], False)

    def test_old_wallet_no_stripe_acct(self):
        profile = MokaProfileFactory()
        Wallet.objects.create(owner=profile, usd_value=876, balance=1345)
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ):
            response = self.client.get(
                path=f"/v1/money/wallet",
                content_type="application/json",
            ).json()
            self.assertEqual(response["balance"], 1345)
            self.assertEqual(response["usd_value"], 876)
            self.assertEqual(response["payout_enabled"], False)

    def test_old_wallet_with_stripe_acct_payout_enabled(self):
        profile = MokaProfileFactory()
        Wallet.objects.create(
            owner=profile, usd_value=876, balance=1345, stripe_connect_account="hello"
        )
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ), mock.patch(
            "stripe.Account.retrieve",
            return_value=PAYOUT_ENABLED_ACCT,
        ):
            response = self.client.get(
                path=f"/v1/money/wallet",
                content_type="application/json",
            ).json()
            self.assertEqual(response["balance"], 1345)
            self.assertEqual(response["usd_value"], 876)
            self.assertEqual(response["payout_enabled"], True)

    def test_old_wallet_with_stripe_acct_payout_disabled(self):
        profile = MokaProfileFactory()
        Wallet.objects.create(
            owner=profile, usd_value=876, balance=1345, stripe_connect_account="hello"
        )
        with mock.patch(
            "money.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ), mock.patch(
            "stripe.Account.retrieve",
            return_value=PAYOUT_DISABLED_ACCT,
        ):
            response = self.client.get(
                path=f"/v1/money/wallet",
                content_type="application/json",
            ).json()
            self.assertEqual(response["balance"], 1345)
            self.assertEqual(response["usd_value"], 876)
            self.assertEqual(response["payout_enabled"], False)


class TestMoveMonthlyToPayout(django.test.TransactionTestCase):
    def test_move_monthly_to_payout(self):
        no_profit_wallets = WalletFactory.create_batch(
            size=10,
        )
        profit_wallets = WalletFactory.create_batch(
            size=10,
            monthly_profit_balance=100,
            monthly_profit_usd_value=99,
            payout_balance=1234,
            payout_usd_value=1234,
        )
        move_monthly_balance_to_payout_balance()

        for wallet in no_profit_wallets:
            wallet.refresh_from_db()
            self.assertEqual(wallet.monthly_profit_balance, 0)
            self.assertEqual(wallet.monthly_profit_usd_value, 0)
            self.assertEqual(wallet.payout_balance, 0)
            self.assertEqual(wallet.payout_usd_value, 0)
        for wallet in profit_wallets:
            wallet.refresh_from_db()
            self.assertEqual(wallet.monthly_profit_balance, 0)
            self.assertEqual(wallet.monthly_profit_usd_value, 0)
            self.assertEqual(wallet.payout_balance, 1334)
            self.assertEqual(wallet.payout_usd_value, 1333)


class TestPayout(django.test.TransactionTestCase):
    def test_invalid_amount(self):
        with mock.patch(
            "stripe.Transfer.create",
            return_value=None,
        ) as mock_transfer_create:
            wallet = WalletFactory(
                usd_value=876,
                balance=1345,
                stripe_connect_account="hello",
                monthly_profit_balance=10000,
                payout_balance=299,
            )
            payout(stripe_handler=StripeHandler())
            mock_transfer_create.assert_not_called()
            wallet.refresh_from_db()
            self.assertEqual(wallet.payout_balance, 299)

    def test_no_stripe_account(self):
        with mock.patch(
            "stripe.Transfer.create",
            return_value=None,
        ) as mock_transfer_create:
            wallet = WalletFactory(
                usd_value=876,
                balance=1345,
                stripe_connect_account=None,
                monthly_profit_balance=10000,
                payout_balance=1500,
            )
            payout(stripe_handler=StripeHandler())
            mock_transfer_create.assert_not_called()
            wallet.refresh_from_db()
            self.assertEqual(wallet.payout_balance, 1500)

    def test_account_not_enabled_for_payout(self):
        with mock.patch(
            "stripe.Transfer.create",
            return_value=None,
        ) as mock_transfer_create, mock.patch(
            "stripe.Account.retrieve",
            return_value=PAYOUT_DISABLED_ACCT,
        ):
            wallet = WalletFactory(
                usd_value=876,
                balance=1345,
                stripe_connect_account="hello",
                monthly_profit_balance=10000,
                monthly_profit_usd_value=9999,
                payout_balance=10000,
                payout_usd_value=9999,
            )
            payout(stripe_handler=StripeHandler())
            mock_transfer_create.assert_not_called()
            wallet.refresh_from_db()
            self.assertEqual(wallet.payout_balance, 10000)
            self.assertEqual(wallet.monthly_profit_balance, 10000)

    def test_success(self):
        with mock.patch(
            "stripe.Transfer.create",
            return_value=None,
        ) as mock_transfer_create, mock.patch(
            "stripe.Account.retrieve",
            return_value=PAYOUT_ENABLED_ACCT,
        ):
            wallet = WalletFactory(
                usd_value=876,
                balance=1345,
                stripe_connect_account=PAYOUT_ENABLED_ACCT["id"],
                monthly_profit_balance=10000,
                payout_balance=1234,
                payout_usd_value=1111.1234,
            )
            payout(stripe_handler=StripeHandler())
            mock_transfer_create.assert_called_with(
                amount=math.floor(1111.1234 * 0.9),
                currency="usd",
                destination=PAYOUT_ENABLED_ACCT["id"],
                metadata={
                    "coins": 1234,
                    "eligible_value": 1111.1234,
                    "platform_fee": 111,
                },
            )
            wallet.refresh_from_db()
            self.assertEqual(wallet.balance, 1345)
            self.assertEqual(wallet.usd_value, 876)
            self.assertEqual(wallet.monthly_profit_balance, 10000)
            self.assertEqual(wallet.monthly_profit_usd_value, 0)
            self.assertEqual(wallet.payout_balance, 0)
            self.assertEqual(wallet.payout_usd_value, 0)
