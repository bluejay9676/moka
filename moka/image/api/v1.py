from datetime import datetime, timedelta, timezone

from common.auth import CloudSchedulerAuthentication, FirebaseAuthentication
from common.errors import MokaBackendGenericError, UnauthorizedError
from common.logger import StructuredLogger
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators import csrf
from episode.models import Episode
from image.api.schema import (
    DeletePageInputSchema,
    DeleteThumbnailInputSchema,
    NewImageSchema,
    NewPageInputSchema,
)
from image.models import Image, Page, Storage, Thumbnail
from ninja import Router

router = Router()
logger = StructuredLogger(__name__)


@router.post(
    "/thumbnail/new",
    response=NewImageSchema,
    auth=FirebaseAuthentication(),
)
def create_draft_thumbnail(request):
    try:
        (
            new_draft_thumbnail,
            upload_url,
        ) = Thumbnail.get_new_draft_image_and_signed_upload_url(
            storage=Storage.GOOGLE_CLOUD_STORAGE,
            owner=request.auth,
        )
        return NewImageSchema(id=new_draft_thumbnail.id, signed_upload_url=upload_url)
    except Exception as e:
        logger.exception(
            event_name="NEW_THUMBNAIL_CREATE_FAIL",
            msg=str(e),
        )
        raise MokaBackendGenericError


@router.post(
    "/page/new",
    response=NewImageSchema,
    auth=FirebaseAuthentication(),
)
def create_draft_page(request, input: NewPageInputSchema):
    episode = get_object_or_404(
        Episode.objects.select_related("series__owner"), id=input.episode_id
    )
    if episode.series.is_owner(request.auth):
        try:
            new_draft_page, upload_url = Page.get_new_draft_image_and_signed_upload_url(
                storage=Storage.GOOGLE_CLOUD_STORAGE,
                episode=episode,
                owner=request.auth,
            )
            return NewImageSchema(id=new_draft_page.id, signed_upload_url=upload_url)
        except Exception as e:
            logger.exception(
                event_name="NEW_PAGE_CREATE_FAIL",
                msg=str(e),
            )
    else:
        raise UnauthorizedError


@router.post(
    "/page/delete",
    auth=FirebaseAuthentication(),
)
def remove_page(request, input: DeletePageInputSchema):
    page = get_object_or_404(Page.objects.select_related("owner"), id=input.id)
    if page.owner == request.auth:
        page.delete()
    else:
        raise UnauthorizedError


@router.post(
    "/thumbnail/delete",
    auth=FirebaseAuthentication(),
)
def remove_thumbnail(request, input: DeleteThumbnailInputSchema):
    thumbnail = get_object_or_404(
        Thumbnail.objects.select_related("owner"), id=input.id
    )
    if thumbnail.owner == request.auth:
        thumbnail.delete()
    else:
        raise UnauthorizedError


@router.post(
    "/cleanup",
    auth=CloudSchedulerAuthentication(),
)
@csrf.csrf_exempt
def remove_non_public_images(request):
    """
    Called by scheduler
    """
    logger.info(event_name="CLEANUP_OLD_IMAGES_START")
    Thumbnail.objects.filter(
        ~Q(status=Image.ImageStatus.PUBLIC),
        Q(
            created_at__lt=datetime.now().replace(tzinfo=timezone.utc)
            - timedelta(days=2)
        ),
    ).delete()
    Page.objects.filter(
        ~Q(status=Image.ImageStatus.PUBLIC),
        Q(
            created_at__lt=datetime.now().replace(tzinfo=timezone.utc)
            - timedelta(days=2)
        ),
    ).delete()
    logger.info(event_name="CLEANUP_OLD_IMAGES_DONE")
