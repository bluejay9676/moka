from datetime import datetime
from typing import Optional

from common.logger import StructuredLogger
from common.schema_utils import datetime_encoder
from moka_profile.models import MokaProfile
from ninja import Field, Schema

logger = StructuredLogger(__name__)


class ProfileEditInputSchema(Schema):
    thumbnail_id: Optional[str]
    display_name: Optional[str]
    description: Optional[str]


class ProfileCreateInputSchema(Schema):
    email: str
    password: str
    username: str


class SessionLoginInputSchema(Schema):
    token: str


class ProfileSchema(Schema):
    id: str
    profile_picture_url: Optional[str]
    profile_picture_id: Optional[str]
    display_name: str
    description: Optional[str]
    is_owner: bool = Field(default=False)
    balance: Optional[int]

    is_following: bool = Field(default=False)
    followers: int
    following: int

    class Config(Schema.Config):
        json_encorders = {datetime: datetime_encoder}

    @staticmethod
    def resolve_id(obj: MokaProfile):
        return obj.id

    @staticmethod
    def resolve_profile_picture_url(obj: MokaProfile):
        if obj.thumbnail:
            return obj.thumbnail.signed_cookie

    @staticmethod
    def resolve_profile_picture_id(obj: MokaProfile):
        if obj.thumbnail:
            return obj.thumbnail.id

    @staticmethod
    def resolve_display_name(obj: MokaProfile):
        return obj.get_display_name()

    @staticmethod
    def resolve_description(obj: MokaProfile):
        return obj.description

    @staticmethod
    def resolve_is_owner(_: MokaProfile):
        return False

    @staticmethod
    def resolve_is_following(_: MokaProfile):
        return False

    @staticmethod
    def resolve_followers(obj: MokaProfile):
        return obj.followers.count()

    @staticmethod
    def resolve_following(obj: MokaProfile):
        return obj.following.count()

    @staticmethod
    def resolve_balance(obj: MokaProfile):
        return 0

    @staticmethod
    def resolve_with_profile(profile: MokaProfile):
        ret = {
            "id": profile.id,
            "display_name": profile.get_display_name(),
            "description": profile.description,
            "followers": profile.followers.count(),
            "following": profile.following.count(),
        }
        if profile.thumbnail:
            ret["profile_picture_url"] = profile.thumbnail.signed_cookie
            ret["profile_picture_id"] = profile.thumbnail.id
        return ret

    @staticmethod
    def resolve_with_profile_and_caller(
        profile: MokaProfile, caller: Optional[MokaProfile]
    ):
        ret = ProfileSchema.resolve_with_profile(profile)
        if caller is not None:
            ret["is_owner"] = profile.id == caller.id
            ret["is_following"] = caller.followings.filter(id=profile.id).exists()
            if ret["is_owner"]:
                ret["balance"] = profile.get_balance()
        return ret
