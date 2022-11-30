from datetime import datetime
from typing import List, Optional

from collection.models import FollowingCollection
from common.logger import StructuredLogger
from common.schema_utils import datetime_encoder
from episode.api.schema import EpisodeIdSchema
from moka_profile.models import MokaProfile
from ninja import Field, Schema
from series.models import Series

logger = StructuredLogger(__name__)


class SeriesEditInputSchema(Schema):
    thumbnail_id: Optional[str] = Field(default=None)
    title: str
    description: Optional[str]
    status: str
    tags: list


class SeriesEpisodesOrderInputSchema(Schema):
    start: int
    end: int
    new_episode_ordering: List[EpisodeIdSchema]  # ascending order


class SeriesMetaDataSchema(Schema):
    thumbnail_id: Optional[str]
    thumbnail_url: Optional[str] = Field(default=None)
    artist_id: str
    artist_name: str
    series_id: str
    series_title: str
    tags: list
    description: Optional[str]

    status: str

    is_owner: Optional[bool] = Field(default=False)
    is_following: Optional[bool] = Field(default=False)

    class Config(Schema.Config):
        json_encorders = {datetime: datetime_encoder}

    def resolve_thumbnail_url(self, series: Series):
        if series.thumbnail:
            return series.thumbnail.signed_cookie

    def resolve_thumbnail_id(self, series: Series):
        if series.thumbnail:
            return series.thumbnail.id

    def resolve_artist_id(self, series: Series):
        return series.owner.id

    def resolve_artist_name(self, series: Series):
        return series.owner.get_display_name()

    def resolve_series_id(self, series: Series):
        return series.id

    def resolve_series_title(self, series: Series):
        return series.title

    def resolve_tags(self, series: Series):
        return series.get_tags()

    def resolve_description(self, series: Series):
        return series.description

    def resolve_is_owner(self, series: Series):
        return None

    def resolve_is_following(self, series: Series):
        return None

    def resolve_status(self, series: Series):
        return series.status

    @staticmethod
    def resolve_with_series(series: Series):
        ret = {
            "artist_id": series.owner.id,
            "artist_name": series.owner.get_display_name(),
            "series_id": series.id,
            "series_title": series.title,
            "tags": series.get_tags(),
            "description": series.description,
            "status": series.status,
        }
        if series.thumbnail:
            ret["thumbnail_url"] = series.thumbnail.signed_cookie
            ret["thumbnail_id"] = series.thumbnail.id
        return ret

    @staticmethod
    def resolve_with_series_and_caller(series: Series, caller: Optional[MokaProfile]):
        ret = SeriesMetaDataSchema.resolve_with_series(series)
        if caller is not None:
            ret["is_owner"] = series.is_owner(caller)
            following_collection, _ = FollowingCollection.objects.get_or_create(
                owner=caller
            )
            ret["is_following"] = following_collection.series.filter(
                id=series.id
            ).exists()
        return ret
