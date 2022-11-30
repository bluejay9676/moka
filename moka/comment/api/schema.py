from __future__ import annotations

from datetime import datetime
from typing import Optional

from comment.models import Comment
from common.schema_utils import datetime_encoder
from moka_profile.models import MokaProfile
from ninja import Schema


class CommentPostInputSchema(Schema):
    content: str
    episode_id: str


class ReplyPostInputSchema(Schema):
    content: str
    episode_id: str
    parent_comment_id: str


class CommentUpdateInputSchema(Schema):
    content: str


class CommentSchema(Schema):
    id: str

    commenter_id: str
    commenter_display_name: str

    content: str

    liked: bool
    is_mine: bool

    likes: int

    # NOTE: children: List["CommentSchema"] = Field(default=[])
    children: int

    created_at: datetime

    class Config(Schema.Config):
        json_encorders = {datetime: datetime_encoder}

    @staticmethod
    def resolve_id(obj: Comment):
        return obj.id

    @staticmethod
    def resolve_commenter_id(obj: Comment):
        return obj.commenter.id

    @staticmethod
    def resolve_commenter_display_name(obj: Comment):
        return obj.commenter.display_name

    @staticmethod
    def resolve_content(obj: Comment):
        return obj.content

    @staticmethod
    def resolve_is_mine(obj: Comment):
        return False

    @staticmethod
    def resolve_liked(obj: Comment):
        return False

    @staticmethod
    def resolve_likes(obj: Comment):
        return obj.likes.count()

    @staticmethod
    def resolve_children(obj: Comment):
        return obj.replies.count()

    @staticmethod
    def resolve_created_at(obj: Comment):
        return obj.created_at

    @staticmethod
    def resolve_with_comment(obj: Comment):
        ret = {
            "id": CommentSchema.resolve_id(obj),
            "commenter_id": CommentSchema.resolve_commenter_id(obj),
            "commenter_display_name": CommentSchema.resolve_commenter_display_name(obj),
            "content": CommentSchema.resolve_content(obj),
            "liked": CommentSchema.resolve_liked(obj),
            "is_mine": CommentSchema.resolve_is_mine(obj),
            "likes": CommentSchema.resolve_likes(obj),
            "children": CommentSchema.resolve_children(obj),
            "created_at": CommentSchema.resolve_created_at(obj),
        }
        return ret

    @staticmethod
    def resolve_with_comment_and_caller(obj: Comment, caller: Optional[MokaProfile]):
        ret = CommentSchema.resolve_with_comment(obj)
        if caller is not None:
            ret["liked"] = obj.likes.filter(liker=caller).exists()
            ret["is_mine"] = obj.commenter == caller
        return ret
