from datetime import datetime, timedelta, timezone
from typing import List, Optional

from common.auth import (
    CloudSchedulerAuthentication,
    FirebaseAuthentication,
    FirebaseOptionalAuthentication,
)
from common.errors import ErrorResponse, MokaBackendGenericError, UnauthorizedError
from common.logger import StructuredLogger
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.views.decorators import csrf
from episode.api.schema import (
    EpisodeCreateNewInputSchema,
    EpisodeEditInputSchema,
    EpisodeFetchStatus,
    EpisodeMetaDataSchema,
    EpisodeSchema,
)
from episode.models import Episode, LikeEpisode, PurchaseEpisode
from image.models import Image, Page, Thumbnail
from moka_profile.models import MokaProfile
from ninja import Router
from series.models import Series

router = Router()
logger = StructuredLogger(__name__)


@router.get(
    "/{int:id}/next",
    response=Optional[EpisodeSchema],
)
@csrf.csrf_exempt
def next_public_episode(request, id: int):
    current_episode = get_object_or_404(
        Episode.objects.select_related("series__owner"),
        id=id,
    )
    return (
        Episode.objects.filter(
            series=current_episode.series,
            episode_number__gt=current_episode.episode_number,
            status__in=[
                Episode.EpisodeStatus.PUBLIC,
                Episode.EpisodeStatus.PRE_RELEASE,
            ],
            is_banned=False,
            series__is_banned=False,
            series__owner__is_banned=False,
        )
        .order_by("episode_number")
        .first()
    )


@router.get(
    "/{int:id}/prev",
    response=Optional[EpisodeSchema],
)
@csrf.csrf_exempt
def prev_public_episode(request, id: int):
    current_episode = get_object_or_404(
        Episode.objects.select_related("series__owner"),
        id=id,
    )
    return (
        Episode.objects.filter(
            series=current_episode.series,
            episode_number__lt=current_episode.episode_number,
            status__in=[
                Episode.EpisodeStatus.PUBLIC,
                Episode.EpisodeStatus.PRE_RELEASE,
            ],
            is_banned=False,
            series__is_banned=False,
            series__owner__is_banned=False,
        )
        .order_by("-episode_number")
        .first()
    )


@router.get(
    "/{int:id}",
    response=EpisodeSchema,
    auth=FirebaseAuthentication(),
    description="Used to fetch episode during edit",
)
def get_episode(request, id: int):
    episode = get_object_or_404(
        Episode.objects.select_related("series__owner").filter(
            is_banned=False,
            series__is_banned=False,
            series__owner__is_banned=False,
        ),
        id=id,
    )
    if episode.series.is_owner(request.auth):
        return EpisodeSchema.resolve_with_episode_and_caller(
            episode,
            request.auth if isinstance(request.auth, MokaProfile) else None,
            EpisodeFetchStatus.ACCESSIBLE,
        )
    else:
        raise UnauthorizedError


def incr_view_and_resolve_episode_with_profile(
    episode: Episode, profile: Optional[MokaProfile], fetch_status: str
):
    episode.incr_view()
    return EpisodeSchema.resolve_with_episode_and_caller(
        obj=episode,
        caller=profile,
        fetch_status=fetch_status,
    )


@router.get(
    "/{int:id}/public",
    response=EpisodeSchema,
    auth=FirebaseOptionalAuthentication(),
    description="Fetch episode as a reader, not the author.",
)
def get_public_episode(request, id: int):
    episode = get_object_or_404(
        Episode.objects.select_related("series__owner"),
        id=id,
        status__in=[
            Episode.EpisodeStatus.PUBLIC,
            Episode.EpisodeStatus.PRE_RELEASE,
        ],
        series__status=Series.SeriesStatus.PUBLIC,
        is_banned=False,
        series__is_banned=False,
        series__owner__is_banned=False,
    )
    if episode.status == Episode.EpisodeStatus.PRE_RELEASE or episode.is_premium:
        # Needs to be authenticated
        if isinstance(request.auth, MokaProfile):
            if (
                episode.series.is_owner(request.auth)
                or episode.price <= 0
                or PurchaseEpisode.objects.filter(
                    episode=episode,
                    profile=request.auth,
                ).exists()
            ):
                return incr_view_and_resolve_episode_with_profile(
                    episode=episode,
                    profile=request.auth
                    if isinstance(request.auth, MokaProfile)
                    else None,
                    fetch_status=EpisodeFetchStatus.ACCESSIBLE,
                )
        return incr_view_and_resolve_episode_with_profile(
            episode=episode,
            profile=request.auth if isinstance(request.auth, MokaProfile) else None,
            fetch_status=EpisodeFetchStatus.NEED_PURCHASE,
        )
    else:
        return incr_view_and_resolve_episode_with_profile(
            episode=episode,
            profile=request.auth if isinstance(request.auth, MokaProfile) else None,
            fetch_status=EpisodeFetchStatus.ACCESSIBLE,
        )


@router.post(
    "/{int:id}/edit",
    response={200: EpisodeMetaDataSchema, 400: ErrorResponse},
    auth=FirebaseAuthentication(),
)
def edit_episode(request, id: int, input: EpisodeEditInputSchema):
    episode = get_object_or_404(
        Episode.objects.select_related("series__owner").filter(
            is_banned=False,
            series__is_banned=False,
            series__owner__is_banned=False,
        ),
        id=id,
    )
    caller_profile: MokaProfile = request.auth
    if episode.series.is_owner(caller_profile):
        try:
            with transaction.atomic():
                if input.thumbnail_id is not None:
                    episode.thumbnail = get_object_or_404(
                        Thumbnail.objects,
                        id=input.thumbnail_id,
                    )
                    episode.thumbnail.status = Image.ImageStatus.PUBLIC
                    episode.thumbnail.save()
                else:
                    if episode.thumbnail:
                        episode.thumbnail.status = Image.ImageStatus.REMOVED
                        episode.thumbnail.save()
                        episode.thumbnail = None

                episode.title = input.title
                episode.price = max(input.price, 0)
                episode.is_premium = input.is_premium
                if episode.price <= 0:
                    episode.is_premium = False
                episode.is_nsfw = input.is_nsfw

                # If the input release date (in UTC) is
                # earlier than the current time, it is set as PUBLIC,
                # otherwise set as PRE_RELEASE
                current_time = datetime.now().replace(tzinfo=timezone.utc)
                if input.release_scheduled_date <= current_time:
                    # Don't update publish date if the episode has already been published
                    if episode.status != Episode.EpisodeStatus.PUBLIC:
                        episode.publish_date = datetime.now().replace(
                            tzinfo=timezone.utc
                        )
                    episode.status = Episode.EpisodeStatus.PUBLIC
                else:
                    if episode.status != Episode.EpisodeStatus.PUBLIC:
                        episode.release_scheduled_date = input.release_scheduled_date
                        episode.publish_date = input.release_scheduled_date
                        episode.status = Episode.EpisodeStatus.PRE_RELEASE
                    else:
                        return 400, ErrorResponse(
                            message="You can not set an already published episode to pre-release"
                        )

                episode.is_scroll_view = input.is_scroll_view

                episode.save()

                edit_episode_page_order(
                    episode=episode,
                    new_order=input.new_page_ordering,
                )

            return EpisodeMetaDataSchema.resolve_with_episode_and_caller(
                episode,
                caller_profile,
            )
        except IntegrityError as e:
            # Rollback
            logger.exception(
                event_name="EDIT_EPISODE_ROLLBACK",
                msg=str(e),
                episode=id,
            )
            raise MokaBackendGenericError
        except Exception as e:
            logger.exception(
                event_name="EDIT_EPISODE_ERROR",
                msg=str(e),
                episode=id,
            )
            raise MokaBackendGenericError
    else:
        raise UnauthorizedError


def edit_episode_page_order(episode: Episode, new_order: List):
    try:
        # This will include DRAFT (newly added) images
        # and PUBLIC (already added before) images
        # {id: page object}
        pages = episode.pages.exclude(status=Episode.EpisodeStatus.REMOVED).in_bulk(
            field_name="id"
        )

        # {id: new page order}
        new_page_ordering = {page.id: idx + 1 for idx, page in enumerate(new_order)}

        bulk_update_pages = []

        # Loop through all the pages linked to
        for page_id, page_object in pages.items():
            if page_id in new_page_ordering:
                page_object.order = new_page_ordering[page_id]
                page_object.status = Image.ImageStatus.PUBLIC
            else:
                # Unused DRAFT images and PUBLIC images should be REMOVED
                page_object.status = Image.ImageStatus.REMOVED
            bulk_update_pages.append(page_object)

        Page.objects.bulk_update(bulk_update_pages, ["order", "status"])

    except Exception as e:
        logger.exception(
            event_name="EDIT_EPISODE_PAGE_ORDER_ERROR",
            msg=str(e),
            episode=id,
        )
        raise MokaBackendGenericError


@router.post(
    "/new",
    response=EpisodeSchema,
    auth=FirebaseAuthentication(),
)
def create_new_draft_episode(request, input: EpisodeCreateNewInputSchema):
    try:
        series = get_object_or_404(
            Series.objects,
            id=int(input.series_id),
        )
        if series.is_owner(request.auth):
            try:
                latest_episode_number = (
                    series.episodes.latest("episode_number").episode_number + 1
                )
            except Episode.DoesNotExist:
                latest_episode_number = 1

            episode = Episode.objects.create(
                series=series,
                status=Episode.EpisodeStatus.DRAFT,
                episode_number=latest_episode_number,
            )
            return EpisodeSchema.resolve_with_episode_and_caller(
                episode,
                request.auth,
                EpisodeFetchStatus.ACCESSIBLE,
            )
        else:
            raise UnauthorizedError
    except Exception as e:
        logger.exception(
            event_name="ADD_NEW_EPISODE_ERROR",
            msg=str(e),
        )
        raise MokaBackendGenericError


@router.post(
    "/{int:id}/delete",
    response=None,
    auth=FirebaseAuthentication(),
)
def delete_episode(request, id: int):
    deleting_episode: Episode = get_object_or_404(
        Episode.objects.select_related("series__owner"),
        id=id,
    )
    if deleting_episode.series.is_owner(request.auth):
        try:
            # Resort the following episodes
            following_episodes = Episode.objects.filter(
                series=deleting_episode.series,
                episode_number__gt=deleting_episode.episode_number,
            ).order_by("episode_number")

            bulk_episode_update = []
            episode_number = deleting_episode.episode_number
            for next_episode in following_episodes:
                next_episode.episode_number = episode_number
                bulk_episode_update.append(next_episode)
                episode_number += 1

            # Run update and delete in a transaction
            with transaction.atomic():
                Episode.objects.bulk_update(bulk_episode_update, ["episode_number"])
                deleting_episode.delete_cached_views()
                deleting_episode.delete()
        except IntegrityError as e:
            # Rollback
            logger.exception(
                event_name="DELETE_EPISODE_ROLLBACK",
                msg=str(e),
                episode=id,
            )
            raise MokaBackendGenericError
        except Exception as e:
            logger.exception(
                event_name="DELETE_EPISODE_ERROR",
                msg=str(e),
                episode=id,
            )
            raise MokaBackendGenericError
    else:
        raise UnauthorizedError


@router.post(
    "/{int:id}/like",
    response=None,
    auth=FirebaseAuthentication(),
)
def like_episode(request, id: int):
    profile: MokaProfile = request.auth
    episode: Episode = get_object_or_404(
        Episode.objects,
        id=id,
    )
    like = LikeEpisode(
        episode=episode,
        profile=profile,
    )
    like.save()


@router.post(
    "/{int:id}/unlike",
    response=None,
    auth=FirebaseAuthentication(),
)
def unlike_episode(request, id: int):
    profile: MokaProfile = request.auth
    episode: Episode = get_object_or_404(
        Episode.objects,
        id=id,
    )
    LikeEpisode.objects.filter(
        episode=episode,
        profile=profile,
    ).delete()


@router.post(
    "/view-sync-and-update-trend-score",
    auth=CloudSchedulerAuthentication(),
)
@csrf.csrf_exempt
def sync_views_and_update_trend_score(request):
    logger.info(event_name="SYNC_VIEW_AND_TREND_SCORE_UPDATE_START")
    bulk_episode_update = []

    # This should match trending_feed episode filter query params
    public_episodes = Episode.objects.select_related(
        "thumbnail",
        "series__owner",
    ).filter(
        status=Episode.EpisodeStatus.PUBLIC,
        series__status=Series.SeriesStatus.PUBLIC,
    )

    for episode in public_episodes:
        # Get last 5 days of likes
        num_recent_likes = LikeEpisode.objects.filter(
            episode=episode,
            created_at__gt=datetime.now().replace(tzinfo=timezone.utc)
            - timedelta(days=5),
        ).count()
        num_views = episode.get_buffer_views()

        episode.views += num_views

        # Calculate trend_score
        episode.trend_score = num_recent_likes * 0.7 + episode.views * 1

        # Clear out view count
        episode.clear_cached_views()
        bulk_episode_update.append(episode)

    Episode.objects.bulk_update(bulk_episode_update, ["views", "trend_score"])

    logger.info(
        event_name="SYNC_VIEW_AND_TREND_SCORE_UPDATE_DONE",
        updated_cnt=len(bulk_episode_update),
    )


@router.post(
    "/publish-episodes",
    auth=CloudSchedulerAuthentication(),
)
@csrf.csrf_exempt
def publish_episodes(request):
    logger.info(event_name="PUBLISH_EPISODES_START")
    bulk_episode_update = []

    current_time = datetime.now().replace(tzinfo=timezone.utc)
    to_publish_episodes = Episode.objects.select_related("series__owner").filter(
        status=Episode.EpisodeStatus.PRE_RELEASE,
        release_scheduled_date__lt=current_time,
    )
    for episode in to_publish_episodes:
        episode.status = Episode.EpisodeStatus.PUBLIC
        episode.publish_date = episode.release_scheduled_date
        if not episode.is_premium:
            episode.price = 0
        bulk_episode_update.append(episode)

    Episode.objects.bulk_update(
        bulk_episode_update, ["status", "publish_date", "price"]
    )

    logger.info(
        event_name="PUBLISH_EPISODES_DONE",
        updated_cnt=len(bulk_episode_update),
    )
