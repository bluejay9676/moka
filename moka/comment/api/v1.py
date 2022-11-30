from typing import List

from comment.api.schema import (
    CommentPostInputSchema,
    CommentSchema,
    CommentUpdateInputSchema,
    ReplyPostInputSchema,
)
from comment.models import Comment, LikeComment
from common.auth import FirebaseAuthentication, FirebaseOptionalAuthentication
from common.logger import StructuredLogger
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.views.decorators import csrf
from episode.models import Episode
from moka_profile.models import MokaProfile
from ninja import Router

router = Router()
logger = StructuredLogger(__name__)


@router.post(
    "/comment",
    response=CommentSchema,
    auth=FirebaseAuthentication(),
)
def post_comment(request, input: CommentPostInputSchema):
    episode = get_object_or_404(Episode.objects, id=input.episode_id)
    new_comment = Comment.objects.create(
        commenter=request.auth,
        episode=episode,
        content=input.content,
    )
    return CommentSchema.resolve_with_comment_and_caller(
        new_comment,
        request.auth,
    )


@router.post(
    "/reply",
    response=CommentSchema,
    auth=FirebaseAuthentication(),
)
def reply(request, input: ReplyPostInputSchema):
    episode = get_object_or_404(Episode.objects, id=input.episode_id)
    parent_comment = get_object_or_404(Comment.objects, id=input.parent_comment_id)
    reply = Comment.objects.create(
        commenter=request.auth,
        episode=episode,
        parent=parent_comment,
        content=input.content,
    )
    return CommentSchema.resolve_with_comment_and_caller(
        reply,
        request.auth,
    )


@router.post(
    "/{int:id}/update",
    response=CommentSchema,
    auth=FirebaseAuthentication(),
)
def update_comment(request, id: int, input: CommentUpdateInputSchema):
    comment = get_object_or_404(
        Comment.objects.filter(
            commenter=request.auth,
        ),
        id=id,
    )
    comment.content = input.content
    comment.save()
    return CommentSchema.resolve_with_comment_and_caller(
        comment,
        request.auth,
    )


@router.post(
    "/{int:id}/like",
    response=None,
    auth=FirebaseAuthentication(),
)
def like_comment(request, id: int):
    comment = get_object_or_404(
        Comment.objects,
        id=id,
    )
    LikeComment.objects.create(
        comment=comment,
        liker=request.auth,
    )


@router.post(
    "/{int:id}/unlike",
    response=None,
    auth=FirebaseAuthentication(),
)
def unlike_comment(request, id: int):
    comment = get_object_or_404(
        Comment.objects,
        id=id,
    )
    LikeComment.objects.filter(
        comment=comment,
        liker=request.auth,
    ).delete()


@router.post(
    "/{int:id}/delete",
    response=None,
    auth=FirebaseAuthentication(),
)
def delete_comment(request, id: int):
    Comment.objects.filter(
        id=id,
        commenter=request.auth,
    ).delete()


@router.get(
    "/load-episode/{int:episode_id}",
    response=List[CommentSchema],
    auth=FirebaseOptionalAuthentication(),
)
@csrf.csrf_exempt
def load_episode_comments(request, episode_id: int, offset: int = 0):
    """
    Return 10 most liked comments given the offset
    """
    top_comments = (
        Comment.objects.filter(
            episode__id=episode_id,
            parent=None,
        )
        .select_related(
            "commenter",
        )
        .annotate(num_likes=Count("like"))
        .order_by("-num_likes")[offset : offset + 10]
    )

    return [
        CommentSchema.resolve_with_comment_and_caller(
            comment, request.auth if isinstance(request.auth, MokaProfile) else None
        )
        for comment in top_comments
    ]


@router.get(
    "/load-reply/{int:parent_comment_id}",
    response=List[CommentSchema],
    auth=FirebaseOptionalAuthentication(),
)
@csrf.csrf_exempt
def load_replies(request, parent_comment_id: int, offset: int = 0):
    """
    Return 10 most liked replies given the offset
    """
    top_replies = (
        Comment.objects.filter(
            parent__id=parent_comment_id,
        )
        .select_related(
            "commenter",
        )
        .annotate(num_likes=Count("like"))
        .order_by("-num_likes")[offset : offset + 10]
    )

    return [
        CommentSchema.resolve_with_comment_and_caller(
            comment, request.auth if isinstance(request.auth, MokaProfile) else None
        )
        for comment in top_replies
    ]
