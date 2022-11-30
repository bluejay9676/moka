from datetime import datetime
from typing import Optional

from common.logger import StructuredLogger
from common.schema_utils import datetime_encoder
from episode.models import Episode
from ninja import Schema

logger = StructuredLogger(__name__)


class FeedInputSchema(Schema):
    class Config(Schema.Config):
        pass


class FeedItemSchema(Schema):
    thumbnail_url: Optional[str]
    artist_id: str
    artist_name: Optional[str]
    series_id: str
    series_title: Optional[str]
    episode_id: str
    episode_title: Optional[str]
    views: int
    tags: list
    likes: int

    is_premium: bool
    is_nsfw: bool
    release_date: datetime

    class Config(Schema.Config):
        json_encorders = {datetime: datetime_encoder}

    def resolve_thumbnail_url(self, obj: Episode):
        try:
            if obj.thumbnail:
                return obj.thumbnail.signed_cookie
        except Exception:
            logger.exception(
                event_name="FEED_ITEM_ERROR", msg="Failed to get thumbnail url"
            )
        return

    def resolve_episode_id(self, obj: Episode):
        return obj.id

    def resolve_episode_title(self, obj: Episode):
        return obj.title

    def resolve_artist_id(self, obj: Episode):
        return obj.series.owner.id

    def resolve_artist_name(self, obj: Episode):
        return obj.series.owner.get_display_name()

    def resolve_series_id(self, obj: Episode):
        return obj.series.id

    def resolve_series_title(self, obj: Episode):
        return obj.series.title

    def resolve_views(self, obj: Episode):
        return obj.get_views()

    def resolve_tags(self, obj: Episode):
        return obj.series.get_tags()

    def resolve_likes(self, obj: Episode):
        return obj.get_likes()

    def resolve_is_nsfw(self, obj: Episode):
        return obj.is_nsfw

    def resolve_is_premium(self, obj: Episode):
        return obj.is_premium

    def resolve_release_date(self, obj: Episode):
        return obj.publish_date
