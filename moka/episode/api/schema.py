from datetime import datetime, timezone
from typing import List, Optional

from common.logger import StructuredLogger
from common.schema_utils import datetime_encoder
from episode.models import Episode
from image.api.schema import PageIdSchema, PageSchema
from image.models import Image
from moka_profile.models import MokaProfile
from ninja import Schema
from pydantic import Field

logger = StructuredLogger(__name__)


class EpisodeIdSchema(Schema):
    id: int


class EpisodeEditInputSchema(Schema):
    thumbnail_id: Optional[str] = Field(default=None)
    title: str
    is_scroll_view: bool = Field(default=False)
    new_page_ordering: List[PageIdSchema]  # ascending order
    release_scheduled_date: datetime = Field(
        default=datetime.now().replace(tzinfo=timezone.utc)
    )
    price: int = Field(default=0)
    is_premium: bool = Field(default=False)
    is_nsfw: bool = Field(default=False)


class EpisodeCreateNewInputSchema(Schema):
    series_id: str


class EpisodeFetchStatus:
    NEED_PURCHASE = "NEED_PURCHASE"
    ACCESSIBLE = "ACCESSIBLE"


class EpisodeMetaDataSchema(Schema):
    id: str

    thumbnail_url: Optional[str]
    thumbnail_id: Optional[str]
    views: int
    is_premium: bool
    price: int
    release_date: Optional[datetime]
    title: str

    likes: int

    series_id: str
    series_title: str

    is_owner: bool = Field(False)
    status: str

    is_liked: bool = Field(False)

    is_scroll_view: bool = Field(False)

    is_nsfw: bool = Field(False)

    class Config(Schema.Config):
        json_encorders = {datetime: datetime_encoder}

    @staticmethod
    def resolve_id(obj: Episode):
        return obj.id

    @staticmethod
    def resolve_thumbnail_url(obj: Episode):
        try:
            if obj.thumbnail:
                return obj.thumbnail.signed_cookie
        except Exception:
            logger.exception(
                event_name="EPISODE_ERROR", msg="Failed to get thumbnail url"
            )
        return

    @staticmethod
    def resolve_thumbnail_id(obj: Episode):
        try:
            if obj.thumbnail:
                return obj.thumbnail.id
        except Exception:
            logger.exception(
                event_name="EPISODE_ERROR", msg="Failed to get thumbnail id"
            )
        return

    @staticmethod
    def resolve_views(obj: Episode):
        return obj.get_views()

    @staticmethod
    def resolve_is_premium(obj: Episode):
        return obj.is_premium

    @staticmethod
    def resolve_price(obj: Episode):
        return obj.price

    @staticmethod
    def resolve_release_date(obj: Episode):
        return obj.publish_date

    @staticmethod
    def resolve_title(obj: Episode):
        return obj.title

    @staticmethod
    def resolve_likes(obj: Episode):
        return obj.get_likes()

    @staticmethod
    def resolve_series_id(obj: Episode):
        return obj.series.id

    @staticmethod
    def resolve_series_title(obj: Episode):
        return obj.series.title

    @staticmethod
    def resolve_status(obj: Episode):
        if obj.series.status == Episode.EpisodeStatus.PUBLIC:
            return obj.status
        elif obj.series.status == Episode.EpisodeStatus.DRAFT:
            return Episode.EpisodeStatus.DRAFT
        else:
            raise RuntimeError("Episode of removed series should not be shown")

    @staticmethod
    def resolve_is_scroll_view(obj: Episode):
        return obj.is_scroll_view

    @staticmethod
    def resolve_is_nsfw(obj: Episode):
        return obj.is_nsfw

    @staticmethod
    def resolve_with_episode(obj: Episode):
        ret = {
            "id": EpisodeMetaDataSchema.resolve_id(obj),
            "views": EpisodeMetaDataSchema.resolve_views(obj),
            "is_premium": EpisodeMetaDataSchema.resolve_is_premium(obj),
            "price": EpisodeMetaDataSchema.resolve_price(obj),
            "release_date": EpisodeMetaDataSchema.resolve_release_date(obj),
            "title": EpisodeMetaDataSchema.resolve_title(obj),
            "likes": EpisodeMetaDataSchema.resolve_likes(obj),
            "series_id": EpisodeMetaDataSchema.resolve_series_id(obj),
            "series_title": EpisodeMetaDataSchema.resolve_series_title(obj),
            "status": EpisodeMetaDataSchema.resolve_status(obj),
            "is_scroll_view": EpisodeMetaDataSchema.resolve_is_scroll_view(obj),
            "is_nsfw": EpisodeMetaDataSchema.resolve_is_nsfw(obj),
        }
        if obj.thumbnail:
            ret["thumbnail_url"] = EpisodeMetaDataSchema.resolve_thumbnail_url(obj)
            ret["thumbnail_id"] = EpisodeMetaDataSchema.resolve_thumbnail_id(obj)
        return ret

    @staticmethod
    def resolve_with_episode_and_caller(obj: Episode, caller: Optional[MokaProfile]):
        ret = EpisodeMetaDataSchema.resolve_with_episode(obj)
        if caller is not None:
            ret["is_owner"] = obj.series.is_owner(caller)
            ret["is_liked"] = obj.is_liked_by(caller)
        return ret


class EpisodeSchema(Schema):
    metadata: EpisodeMetaDataSchema
    pages: List[PageSchema]
    fetch_status: str = Field(default=EpisodeFetchStatus.NEED_PURCHASE)

    @staticmethod
    def resolve_metadata(obj: Episode):
        return EpisodeMetaDataSchema.resolve_with_episode(obj)

    @staticmethod
    def resolve_metadata_with_caller(obj: Episode, caller: Optional[MokaProfile]):
        return EpisodeMetaDataSchema.resolve_with_episode_and_caller(obj, caller)

    @staticmethod
    def resolve_pages(obj: Episode):
        return [
            PageSchema.resolve_from_page(page)
            for page in obj.pages.filter(
                status=Image.ImageStatus.PUBLIC,
            ).order_by("order")
        ]

    @staticmethod
    def resolve_with_episode(obj: Episode):
        """
        This is used to fetch just the metadata
        """
        return {
            "metadata": EpisodeSchema.resolve_metadata(obj),
            "pages": [],
            "fetch_status": EpisodeFetchStatus.ACCESSIBLE,
        }

    @staticmethod
    def resolve_with_episode_and_caller(
        obj: Episode,
        caller: Optional[MokaProfile],
        fetch_status: str = EpisodeFetchStatus.NEED_PURCHASE,
    ):
        ret = {
            "metadata": EpisodeSchema.resolve_metadata_with_caller(obj, caller),
            "fetch_status": fetch_status,
            "pages": [],
        }
        if fetch_status == EpisodeFetchStatus.ACCESSIBLE:
            ret["pages"] = EpisodeSchema.resolve_pages(obj)
        return ret
