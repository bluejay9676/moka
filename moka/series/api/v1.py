from datetime import datetime, timezone
from typing import List, Optional

from collection.models import FollowingCollection
from common.auth import FirebaseAuthentication, FirebaseOptionalAuthentication
from common.errors import MokaBackendGenericError, UnauthorizedError
from common.logger import StructuredLogger
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators import csrf
from episode.api.schema import EpisodeMetaDataSchema
from episode.models import Episode
from image.models import Image, Thumbnail
from moka_profile.models import MokaProfile
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate
from series.api.schema import (
    SeriesEditInputSchema,
    SeriesEpisodesOrderInputSchema,
    SeriesMetaDataSchema,
)
from series.models import Series

router = Router()
logger = StructuredLogger(__name__)


@router.get(
    "/list",
    response=List[SeriesMetaDataSchema],
)
@csrf.csrf_exempt
@paginate(LimitOffsetPagination)
def get_series_list(request, q: Optional[str] = None):
    query_predicate = (
        Q(status=Series.SeriesStatus.PUBLIC)
        & Q(is_banned=False)
        & Q(owner__is_banned=False)
    )
    if q is not None:
        query_predicate = query_predicate & (
            Q(title__icontains=q)
            | Q(owner__display_name__icontains=q)
            | Q(tags__name__icontains=q)
        )
    return (
        Series.objects.select_related("thumbnail", "owner")
        .filter(query_predicate)
        .order_by("-updated_at")
    )


@router.get(
    "/{int:id}",
    response=SeriesMetaDataSchema,
    auth=FirebaseOptionalAuthentication(),
)
@csrf.csrf_exempt
def get_series(request, id: int):
    series = get_object_or_404(
        Series.objects.select_related("thumbnail", "owner",).filter(
            is_banned=False,
            owner__is_banned=False,
        ),
        id=id,
    )
    return SeriesMetaDataSchema.resolve_with_series_and_caller(
        series,
        request.auth if isinstance(request.auth, MokaProfile) else None,
    )


@router.get(
    "/{int:id}/episodes/public",
    response=List[EpisodeMetaDataSchema],
)
@csrf.csrf_exempt
@paginate(LimitOffsetPagination)
def get_public_series_episodes(request, id: int):
    return (
        Episode.objects.select_related(
            "thumbnail",
            "series",
            "series__owner",
        )
        .filter(
            series=id,
            status__in=[
                Episode.EpisodeStatus.PUBLIC,
                Episode.EpisodeStatus.PRE_RELEASE,
            ],
            is_banned=False,
            series__is_banned=False,
            series__owner__is_banned=False,
        )
        .order_by("-episode_number")
    )


@router.get(
    "/{int:id}/episodes/all",
    response=List[EpisodeMetaDataSchema],
    auth=FirebaseAuthentication(),
    description="List all episodes as a Series owner",
)
@paginate(LimitOffsetPagination)
def get_all_series_episodes(request, id: int):
    return (
        Episode.objects.select_related(
            "thumbnail",
            "series",
        )
        .filter(
            series=id,
        )
        .exclude(
            status=Episode.EpisodeStatus.REMOVED,
        )
        .order_by("-episode_number")
    )


@router.post(
    "/{int:id}/edit",
    response=SeriesMetaDataSchema,
    auth=FirebaseAuthentication(),
)
def edit_series(request, id: int, input: SeriesEditInputSchema):
    series = get_object_or_404(
        Series.objects.select_related("thumbnail", "owner",).filter(
            is_banned=False,
            owner__is_banned=False,
        ),
        id=id,
    )
    caller_profile: MokaProfile = request.auth
    if series.is_owner(caller_profile):
        try:
            with transaction.atomic():
                if input.thumbnail_id is not None:
                    series.thumbnail = get_object_or_404(
                        Thumbnail.objects,
                        id=input.thumbnail_id,
                    )
                    series.thumbnail.status = Image.ImageStatus.PUBLIC
                    series.thumbnail.save()
                else:
                    if series.thumbnail:
                        series.thumbnail.status = Image.ImageStatus.REMOVED
                        series.thumbnail.save()
                        series.thumbnail = None

                series.title = input.title
                series.description = input.description
                if (
                    series.status != Series.SeriesStatus.PUBLIC
                    and input.status == Series.SeriesStatus.PUBLIC
                ):
                    series.publish_date = datetime.now().replace(tzinfo=timezone.utc)
                series.status = input.status
                series.tags.set(input.tags[:5])

                series.save()
            return SeriesMetaDataSchema.resolve_with_series_and_caller(
                series,
                caller_profile,
            )
        except IntegrityError as e:
            # Rollback
            logger.exception(
                event_name="EDIT_SERIES_ROLLBACK",
                msg=str(e),
                series_id=id,
            )
            raise MokaBackendGenericError
        except Exception as e:
            logger.exception(
                event_name="EDIT_SERIES_ERROR",
                msg=str(e),
                series_id=id,
            )
            raise MokaBackendGenericError
    else:
        raise UnauthorizedError


@router.post(
    "/{int:id}/episode/edit",
    response=None,
    auth=FirebaseAuthentication(),
)
def edit_series_episode_order(request, id: int, input: SeriesEpisodesOrderInputSchema):
    series = get_object_or_404(
        Series.objects.select_related("thumbnail", "owner",).filter(
            is_banned=False,
            owner__is_banned=False,
        ),
        id=id,
    )
    caller_profile: MokaProfile = request.auth
    if series.is_owner(caller_profile):
        try:
            episodes = Episode.objects.filter(
                episode_number__gte=input.start,
                episode_number__lte=input.end,
            ).in_bulk(field_name="id")
            bulk_update_episodes = []
            for idx, episode in enumerate(input.new_episode_ordering):
                episodes[episode.id].episode_number = input.start + idx
                bulk_update_episodes.append(episodes[episode.id])
            Episode.objects.bulk_update(bulk_update_episodes, ["episode_number"])
        except Exception as e:
            logger.exception(
                event_name="EDIT_SERIES_EPISODE_ORDER_ERROR",
                msg=str(e),
                series_id=id,
            )
            raise MokaBackendGenericError
    else:
        raise UnauthorizedError


@router.post(
    "/new",
    response=SeriesMetaDataSchema,
    auth=FirebaseAuthentication(),
)
def create_new_draft_series(request):
    try:
        series = Series.objects.create(
            owner=request.auth,
            status=Series.SeriesStatus.DRAFT,
        )
        return SeriesMetaDataSchema.resolve_with_series_and_caller(series, request.auth)
    except Exception as e:
        logger.exception(
            event_name="ADD_NEW_SERIES_ERROR",
            msg=str(e),
        )
        raise MokaBackendGenericError


@router.post(
    "/{int:id}/delete",
    response=None,
    auth=FirebaseAuthentication(),
)
def delete_series(request, id: int):
    series = get_object_or_404(
        Series.objects.select_related(
            "thumbnail",
            "owner",
        ),
        id=id,
    )
    if series.is_owner(request.auth):
        series.delete()
    else:
        raise UnauthorizedError


@router.post(
    "/{int:id}/follow",
    auth=FirebaseAuthentication(),
)
def follow(request, id: int):
    series = get_object_or_404(
        Series.objects.select_related(
            "thumbnail",
            "owner",
        ),
        id=id,
    )
    follow_list, _ = FollowingCollection.objects.get_or_create(
        owner=request.auth,
    )
    follow_list.series.add(series)


@router.post(
    "/{int:id}/unfollow",
    auth=FirebaseAuthentication(),
)
def unfollow(request, id: int):
    series = get_object_or_404(
        Series.objects.select_related(
            "thumbnail",
            "owner",
        ),
        id=id,
    )
    follow_list, _ = FollowingCollection.objects.get_or_create(
        owner=request.auth,
    )
    follow_list.series.remove(series)
