import datetime
from typing import List

from common.auth import FirebaseAuthentication
from common.logger import StructuredLogger
from discovery.api.schema import FeedItemSchema
from django.db.models import Q
from django.views.decorators import csrf
from episode.models import Episode
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate
from series.models import Series

router = Router()
logger = StructuredLogger(__name__)


@router.get(
    "/new",
    response={200: List[FeedItemSchema]},
)
@paginate(LimitOffsetPagination)
@csrf.csrf_exempt
def new_feed(request):
    return (
        Episode.objects.select_related(
            "thumbnail",
            "series__owner",
        )
        .filter(
            status__in=[
                Episode.EpisodeStatus.PUBLIC,
                Episode.EpisodeStatus.PRE_RELEASE,
            ],
            series__status=Series.SeriesStatus.PUBLIC,
            is_banned=False,
            series__is_banned=False,
            series__owner__is_banned=False,
        )
        .order_by("-publish_date")
    )


@router.get(
    "/trending",
    response={200: List[FeedItemSchema]},
)
@paginate(LimitOffsetPagination)
@csrf.csrf_exempt
def trending_feed(request):
    return (
        Episode.objects.select_related(
            "thumbnail",
            "series__owner",
        )
        .filter(
            status__in=[
                Episode.EpisodeStatus.PUBLIC,
                Episode.EpisodeStatus.PRE_RELEASE,
            ],
            series__status=Series.SeriesStatus.PUBLIC,
            publish_date__gt=datetime.datetime.now().replace(
                tzinfo=datetime.timezone.utc
            )
            - datetime.timedelta(days=200),
            is_banned=False,
            series__is_banned=False,
            series__owner__is_banned=False,
        )
        .order_by("-trend_score")
    )


@router.get(
    "/subscribed",
    response={200: List[FeedItemSchema]},
    auth=FirebaseAuthentication(),
)
@paginate(LimitOffsetPagination)
@csrf.csrf_exempt
def subscribed_feed(request):
    # TODO implement subscription
    return []


@router.get(
    "/suggested",
    response={200: List[FeedItemSchema]},
    auth=FirebaseAuthentication(),
)
@paginate(LimitOffsetPagination)
@csrf.csrf_exempt
def suggested_feed(request):
    # TODO implement recommendation
    return []


@router.get("/search/content", response={200: List[FeedItemSchema]})
@paginate(LimitOffsetPagination)
@csrf.csrf_exempt
def search_content(request, q: str):
    return (
        Episode.objects.select_related(
            "thumbnail",
            "series__owner",
        )
        .filter(
            Q(title__icontains=q)
            | Q(series__title__icontains=q)
            | Q(series__owner__display_name__icontains=q)
            | Q(series__tags__name__icontains=q)
            & Q(
                status__in=[
                    Episode.EpisodeStatus.PUBLIC,
                    Episode.EpisodeStatus.PRE_RELEASE,
                ]
            )
            & Q(series__status__exact=Series.SeriesStatus.PUBLIC)
            & Q(is_banned=False)
            & Q(series__is_banned=False)
            & Q(series__owner__is_banned=False)
        )
        .distinct()
    )
