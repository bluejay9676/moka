import datetime
import time
from typing import List, Optional

from common.auth import FirebaseAuthentication, FirebaseOptionalAuthentication
from common.errors import (
    ErrorResponse,
    FirebaseUserFacingError,
    MokaBackendGenericError,
    UnauthorizedError,
)
from common.logger import StructuredLogger
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators import csrf
from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import FirebaseError
from image.models import Image, Thumbnail
from moka_profile.api.schema import (
    ProfileCreateInputSchema,
    ProfileEditInputSchema,
    ProfileSchema,
    SessionLoginInputSchema,
)
from moka_profile.models import Follow, MokaProfile
from ninja import Router
from ninja.pagination import LimitOffsetPagination, paginate
from series.api.schema import SeriesMetaDataSchema
from series.models import Series

router = Router()
logger = StructuredLogger(__name__)


@router.get(
    "/list",
    response=List[ProfileSchema],
)
@csrf.csrf_exempt
@paginate(LimitOffsetPagination)
def get_profile_list(request, q: Optional[str] = None):
    query_predicate = Q(is_banned=False)
    if q is not None:
        query_predicate &= Q(display_name__icontains=q)
    return (
        MokaProfile.objects.filter(query_predicate)
        .select_related("thumbnail")
        .order_by("-created_at")
    )


@router.get(
    "/{int:id}",
    response=ProfileSchema,
    auth=FirebaseOptionalAuthentication(),
)
@csrf.csrf_exempt
def get_profile(request, id: int):
    profile = get_object_or_404(
        MokaProfile.objects.select_related("thumbnail", "wallet").filter(
            is_banned=False
        ),
        id=id,
    )
    return ProfileSchema.resolve_with_profile_and_caller(
        profile,
        request.auth if isinstance(request.auth, MokaProfile) else None,
    )


@router.get(
    "/me",
    response=ProfileSchema,
    auth=FirebaseAuthentication(),
)
def get_my_profile(request):
    try:
        return ProfileSchema.resolve_with_profile_and_caller(
            request.auth,
            request.auth,
        )
    except Exception as e:
        logger.exception(
            event_name="GET_MY_PROFILE",
            msg=str(e),
            profile_id=request.auth.id,
        )
        raise MokaBackendGenericError


@router.get(
    "/{int:id}/works",
    response=List[SeriesMetaDataSchema],
    auth=FirebaseOptionalAuthentication(),
)
@csrf.csrf_exempt
@paginate(LimitOffsetPagination)
def get_works(request, id: int, q: Optional[str] = None):
    # If authorized & owner, get draft series too
    profile = get_object_or_404(
        MokaProfile.objects.select_related("thumbnail", "wallet").filter(
            is_banned=False
        ),
        id=id,
    )
    query_predicate = Q(is_banned=False) & Q(owner__is_banned=False)
    if q is not None:
        query_predicate = query_predicate & (
            Q(title__icontains=q) | Q(tags__name__icontains=q)
        )
    if isinstance(request.auth, MokaProfile) and request.auth.id == profile.id:
        return (
            profile.owning_series.exclude(
                status=Series.SeriesStatus.REMOVED,
            )
            .filter(query_predicate)
            .all()
        )
    else:
        return profile.owning_series.filter(
            query_predicate & Q(status=Series.SeriesStatus.PUBLIC)
        )


@router.post(
    "/{int:id}/edit",
    response={
        200: ProfileSchema,
        400: ErrorResponse,
    },
    auth=FirebaseAuthentication(),
)
def edit_profile(request, id: int, input: ProfileEditInputSchema):
    profile = get_object_or_404(
        MokaProfile.objects.select_related("thumbnail", "wallet").filter(
            is_banned=False
        ),
        id=id,
    )
    if request.auth.id == profile.id:
        try:
            with transaction.atomic():
                if input.thumbnail_id is not None:
                    profile.thumbnail = get_object_or_404(
                        Thumbnail.objects,
                        id=input.thumbnail_id,
                    )
                    profile.thumbnail.status = Image.ImageStatus.PUBLIC
                    profile.thumbnail.save()
                else:
                    # Remove old thumbnail
                    if profile.thumbnail:
                        profile.thumbnail.status = Image.ImageStatus.REMOVED
                        profile.thumbnail.save()
                        profile.thumbnail = None

                profile.description = input.description
                if input.display_name:
                    profile.display_name = input.display_name[:100]

                firebase_auth.update_user(
                    uid=profile.firebase_uid,
                    photo_url=profile.thumbnail.signed_cookie
                    if profile.thumbnail
                    else None,
                    display_name=profile.display_name,
                )

                profile.save()
            return ProfileSchema.resolve_with_profile_and_caller(
                profile,
                request.auth,
            )
        except FirebaseError as e:
            raise FirebaseUserFacingError(e)
        except IntegrityError as e:
            # Rollback
            logger.exception(
                event_name="EDIT_PROFILE_ROLLBACK",
                msg=str(e),
                profile_id=id,
            )
            return 400, ErrorResponse(message=str(e))
        except Exception as e:
            logger.exception(
                event_name="EDIT_PROFILE_ERROR",
                msg=str(e),
                profile=id,
            )
            raise MokaBackendGenericError
    else:
        raise UnauthorizedError


@router.post(
    "/new",
    response={
        200: ProfileSchema,
        400: ErrorResponse,
    },
)
@csrf.csrf_exempt
def create_new_profile(request, input: ProfileCreateInputSchema):
    try:
        try:
            # User might already exist
            user = firebase_auth.get_user_by_email(email=input.email)
        except firebase_auth.UserNotFoundError:
            user = firebase_auth.create_user(
                email=input.email,
                email_verified=False,
                display_name=input.username,
                disabled=False,
            )
        profile = MokaProfile.objects.create(
            firebase_uid=user.uid,
            display_name=input.username,
        )
        firebase_auth.update_user(
            uid=user.uid,
            password=input.password,
        )
        return ProfileSchema.resolve_with_profile_and_caller(profile, profile)
    except FirebaseError as e:
        logger.exception(
            event_name="FIREBASE_ADD_NEW_PROFILE_ERROR",
            msg=str(e),
        )
        raise FirebaseUserFacingError(e)
    except IntegrityError as e:
        # Rollback
        logger.exception(
            event_name="NEW_PROFILE_INTEGRITY_ERROR",
            msg=str(e),
            profile_id=id,
        )
        return 400, ErrorResponse(
            message="Username or email already in use. Please try a different username."
        )
    except Exception as e:
        logger.exception(
            event_name="ADD_NEW_PROFILE_ERROR",
            msg=str(e),
        )
        raise MokaBackendGenericError


@router.post(
    "/delete",
    response=None,
    auth=FirebaseAuthentication(),
)
def delete_profile(request):
    profile = get_object_or_404(
        MokaProfile.objects.select_related("thumbnail", "wallet"),
        id=request.auth.id,
    )
    try:
        with transaction.atomic():
            firebase_auth.delete_user(uid=profile.firebase_uid)
            profile.delete()
    except FirebaseError as e:
        raise FirebaseUserFacingError(e)
    except IntegrityError as e:
        # Rollback
        logger.exception(
            event_name="DELETE_PROFILE_ROLLBACK",
            msg=str(e),
            profile_id=id,
        )
        raise MokaBackendGenericError


@router.post(
    "/sessionLogin",
    response={
        200: None,
        401: ErrorResponse,
    },
)
def session_login(
    request: HttpRequest, input: SessionLoginInputSchema, response: HttpResponse
):
    try:
        decoded_claims = firebase_auth.verify_id_token(input.token)
        # Only process if the user signed in within the last 5 minutes.
        if time.time() - decoded_claims["auth_time"] < 5 * 60:
            # Set session expiration to 1 days.
            expires_in = datetime.timedelta(days=1)
            # Create the session cookie. This will also verify the ID token in the process.
            # The session cookie will have the same claims as the ID token.
            session_cookie = firebase_auth.create_session_cookie(
                input.token, expires_in=expires_in
            )
            # Set cookie policy for session cookie.
            expires = datetime.datetime.now() + expires_in
            response.set_cookie(
                "session",
                session_cookie,
                expires=expires,
                httponly=False,
                secure=False,
                samesite="strict",
                domain=settings.CSRF_COOKIE_DOMAIN,
            )
            return response
        return 401, ErrorResponse(message="Recent sign in required")
    except firebase_auth.InvalidIdTokenError:
        return 401, ErrorResponse(message="Invalid ID token")
    except FirebaseError as e:
        raise FirebaseUserFacingError(e)
    except Exception as e:
        logger.exception(
            event_name="SESSION_LOGIN_FAIL",
            msg=str(e),
        )
        return 401, ErrorResponse(message="Failed to create a session cookie")


@router.post(
    "/sessionLogout",
    auth=FirebaseAuthentication(),
)
def session_logout(request: HttpRequest, response: HttpResponse):
    profile: MokaProfile = request.auth
    try:
        firebase_auth.revoke_refresh_tokens(profile.firebase_uid)
    except FirebaseError as e:
        raise FirebaseUserFacingError(e)
    response.set_cookie("session", expires=0)
    return response


@router.post(
    "/{int:id}/follow",
    auth=FirebaseAuthentication(),
)
def follow(request: HttpRequest, id: int):
    follower = request.auth
    followee = get_object_or_404(
        MokaProfile.objects,
        id=id,
    )
    Follow.objects.get_or_create(
        follower=follower,
        followee=followee,
    )


@router.post(
    "/{int:id}/unfollow",
    auth=FirebaseAuthentication(),
)
def unfollow(request: HttpRequest, id: int):
    Follow.objects.filter(
        follower=request.auth,
        followee__id=id,
    ).delete()
