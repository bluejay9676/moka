import datetime
from typing import List, Optional

import stripe
from common.auth import CloudSchedulerAuthentication, FirebaseAuthentication
from common.errors import ErrorResponse, MokaBackendGenericError
from common.logger import StructuredLogger
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.views.decorators import csrf
from episode.models import Episode
from moka_profile.models import MokaProfile
from money.api.schema import (
    CreateConnectAccountInputSchema,
    CreateConnectAccountOutputSchema,
    DepositCoinsInputSchema,
    DepositCoinsOutputSchema,
    PurchaseEpisodeInputSchema,
    RecentIncomeAmountSchema,
    TipInputSchema,
    TransactionSchema,
    WalletMetaDataOutputSchema,
)
from money.gateway.stripe import BelowMinimumCoinPurchase, StripeHandler
from money.models import Transaction, Wallet
from money.service.transaction import (
    NegativeAmount,
    NotEnoughBalance,
    add_balance_to_wallet,
    move_monthly_balance_to_payout_balance,
    payout,
)
from money.service.transaction import purchase_episode as purchase_episode_transaction
from money.service.transaction import remove_stored_connect_acct_id, send_tip
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate

router = Router()
logger = StructuredLogger(__name__)

stripe_handler = StripeHandler()


def create_wallet_if_needed(profile: MokaProfile):
    try:
        profile.wallet
    except ObjectDoesNotExist:
        Wallet.objects.create(owner=profile)


@router.post(
    "/deposit-coin-session",
    response={200: DepositCoinsOutputSchema, 400: ErrorResponse},
    auth=FirebaseAuthentication(),
)
def deposit_coins(request, input: DepositCoinsInputSchema):
    create_wallet_if_needed(request.auth)

    try:
        session = stripe_handler.create_coin_purchase_checkout_session(
            request.auth,
            input.coins,
            input.current_path,
            input.current_path,
        )
        return DepositCoinsOutputSchema(checkout_session_url=session["url"])
    except BelowMinimumCoinPurchase:
        return 400, ErrorResponse(message="Invalid purchase amount")


@router.post(
    "/webhook",
    response=None,
)
@csrf.csrf_exempt
def stripe_webhook(request: HttpRequest):
    """
    Local Test:
    stripe login
    stripe listen --forward-to localhost:8000/v1/money/webhook
    stripe trigger payment_intent.succeeded
    """
    event = None
    payload = request.body
    sig_header = request.headers["STRIPE_SIGNATURE"]

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_ENDPOINT_SECRET,
        )
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        try:
            add_balance_to_wallet(stripe_handler, session)
        except Exception as e:
            logger.exception(
                event_name="STRIPE_PURCHASE_FULFILL_FAILURE",
                msg=str(e),
                profile_id=session["client_reference_id"],
                session_id=session["id"],
            )
            return 400
    if event["type"] == "account.application.deauthorized":
        connected_account_id = event["account"]
        remove_stored_connect_acct_id(connected_account_id)
    else:
        print("Unhandled event type {}".format(event["type"]))
    return 200


@router.post(
    "/payout-account-create",
    response=CreateConnectAccountOutputSchema,
    auth=FirebaseAuthentication(),
)
def create_stripe_connect_account(request, input: CreateConnectAccountInputSchema):
    # Create wallet first
    profile: MokaProfile = request.auth
    create_wallet_if_needed(profile)

    if profile.wallet.stripe_connect_account is None:
        account = stripe_handler.create_connect_account(profile)

        profile.wallet.stripe_connect_account = account["id"]
        profile.wallet.save()

    onboard_url = stripe_handler.create_account_onboarding(
        profile.wallet.stripe_connect_account,
        input.refresh_url,
        input.return_url,
    )["url"]

    return CreateConnectAccountOutputSchema(
        onboard_url=onboard_url,
    )


@router.post(
    "/purchase-episode",
    response={
        200: None,
        400: ErrorResponse,
    },
    auth=FirebaseAuthentication(),
)
def purchase_episode(request, input: PurchaseEpisodeInputSchema):
    buyer: MokaProfile = request.auth
    episode: Episode = get_object_or_404(
        Episode.objects.select_related("series__owner"),
        id=input.episode_id,
    )
    if (
        (  # Not eligible
            episode.status
            not in [Episode.EpisodeStatus.PUBLIC, Episode.EpisodeStatus.PRE_RELEASE]
        )
        or (  # Public but not premium
            episode.status == Episode.EpisodeStatus.PUBLIC and not episode.is_premium
        )
        or (  # Pre-release but price not set
            episode.status == Episode.EpisodeStatus.PRE_RELEASE and episode.price <= 0
        )
    ):
        return 400, ErrorResponse(message="Episode is not eligible for a purchase")

    try:
        purchase_episode_transaction(buyer, episode)
    except NotEnoughBalance:
        return 400, ErrorResponse(message="Not enough balance")
    except NegativeAmount:
        return 400, ErrorResponse(message="You can't purchase negative amount")
    except IntegrityError as e:
        logger.exception(
            event_name="EPISODE_PURCHASE_ERROR",
            msg=str(e),
            buyer=buyer.id,
            episode_id=episode.id,
        )
        raise MokaBackendGenericError


@router.post("/unlink-stripe-account", response=None, auth=FirebaseAuthentication())
def unlink_stripe_account(request):
    profile: MokaProfile = request.auth
    profile.wallet.stripe_connect_account = None
    profile.wallet.save()


@router.get(
    "/wallet",
    response=WalletMetaDataOutputSchema,
    auth=FirebaseAuthentication(),
)
def get_wallet(request):
    profile: MokaProfile = request.auth
    create_wallet_if_needed(profile)
    return profile.wallet


@router.get(
    "/transactions",
    response=List[TransactionSchema],
    auth=FirebaseAuthentication(),
)
@paginate(LimitOffsetPagination)
def get_transactions(request, type: Optional[str] = None):
    return (
        Transaction.objects.filter(
            Q(type__in=[type] if type is not None else Transaction.Type.names)
            & (Q(recipient=request.auth) | Q(sender=request.auth))
        )
        .select_related("sender", "recipient")
        .order_by("-created_at")
    )


@router.get(
    "/recent-income-amount",
    response=RecentIncomeAmountSchema,
    auth=FirebaseAuthentication(),
)
def get_recent_income(request, days: int = 0):
    agg_transactions = Transaction.objects.filter(
        type=Transaction.Type.PURCHASE,
        recipient=request.auth,
        created_at__gte=datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        - datetime.timedelta(days=days),
    ).aggregate(
        usd_value=Sum("usd_value"),
        coin_amount=Sum("coin_amount"),
    )
    coin_amount = agg_transactions["coin_amount"]
    usd_value = agg_transactions["usd_value"]
    return RecentIncomeAmountSchema(
        amount=coin_amount if coin_amount is not None else 0,
        usd_value=usd_value if usd_value is not None else 0,
    )


@router.post(
    "/tip",
    response={
        200: None,
        400: ErrorResponse,
    },
    auth=FirebaseAuthentication(),
)
def tip(request, input: TipInputSchema):
    if input.profile_id:
        recipient: MokaProfile = get_object_or_404(
            MokaProfile.objects,
            id=input.profile_id,
        )
    elif input.episode_id:
        episode: Episode = get_object_or_404(
            Episode.objects.select_related("series__owner"),
            id=input.episode_id,
        )
        recipient = episode.series.owner
    else:
        return 400, ErrorResponse(message="No profile_id or episode_id is provided")
    try:
        send_tip(
            recipient=recipient,
            sender=request.auth,
            amount=input.amount,
        )
    except NotEnoughBalance:
        return 400, ErrorResponse(message="Not enough balance")
    except NegativeAmount:
        return 400, ErrorResponse(message="You can't tip negative amount")


@router.post(
    "/payout",
    auth=CloudSchedulerAuthentication(),
)
@csrf.csrf_exempt
def monthly_payout(request):
    payout(stripe_handler=stripe_handler)
    logger.info(event_name="PAYOUT_SUCCESSFUL")


@router.post(
    "/move-monthly-to-payout",
    auth=CloudSchedulerAuthentication(),
)
@csrf.csrf_exempt
def move_monthly_to_payout(request):
    move_monthly_balance_to_payout_balance()
    logger.info(event_name="PAYOUT_SUCCESSFUL")
