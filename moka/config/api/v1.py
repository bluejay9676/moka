from http import HTTPStatus
from typing import List

from comment.api.v1 import router as comment_router
from common.auth import (
    FirebaseUserNotFoundError,
    InvalidFirebaseToken,
    NoMatchingProfile,
    UnavailableCookieRedirectLogin,
)
from common.errors import (
    ErrorResponse,
    FirebaseUserFacingError,
    MokaBackendGenericError,
    NotFoundError,
    UnauthorizedError,
)
from discovery.api.v1 import router as discovery_router
from django.http import HttpRequest, JsonResponse
from django.views.decorators import csrf
from episode.api.v1 import router as episode_router
from image.api.v1 import router as image_router
from moka_profile.api.v1 import router as profile_router
from money.api.v1 import router as money_router
from ninja import NinjaAPI
from series.api.v1 import router as series_router
from taggit.models import Tag

api_v1 = NinjaAPI(
    version="1.0.0",
    csrf=True,
    openapi_url=None,
)
api_v1.add_router("discovery/", discovery_router)
api_v1.add_router("series/", series_router)
api_v1.add_router("episode/", episode_router)
api_v1.add_router("profile/", profile_router)
api_v1.add_router("image/", image_router)
api_v1.add_router("money/", money_router)
api_v1.add_router("comment/", comment_router)


@api_v1.exception_handler(InvalidFirebaseToken)
def on_invalid_token(request, exc):
    return api_v1.create_response(
        request,
        ErrorResponse(message="Invalid token supplied"),
        status=HTTPStatus.UNAUTHORIZED,
    )


@api_v1.exception_handler(FirebaseUserNotFoundError)
def on_firebase_no_user(request, exc):
    return api_v1.create_response(
        request,
        ErrorResponse(message="Could not find the user"),
        status=HTTPStatus.UNAUTHORIZED,
    )


@api_v1.exception_handler(UnavailableCookieRedirectLogin)
def on_invalid_cookie_need_login(request, exc):
    return api_v1.create_response(
        request,
        ErrorResponse(
            message="Session cookie was expired or not found. Please login again"
        ),
        status=HTTPStatus.UNAUTHORIZED,
    )


@api_v1.exception_handler(NoMatchingProfile)
def on_no_matching_moka_profile(request, exc):
    return api_v1.create_response(
        request,
        ErrorResponse(message="No matching user profile found"),
        status=HTTPStatus.UNAUTHORIZED,
    )


@api_v1.exception_handler(MokaBackendGenericError)
def on_generic_error(request, exc):
    return api_v1.create_response(
        request,
        ErrorResponse(message="Server was unable to process the request"),
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


@api_v1.exception_handler(UnauthorizedError)
def on_unauthorized_error(request, exc):
    return api_v1.create_response(
        request,
        ErrorResponse(message="User is not authorized to perform this action"),
        status=HTTPStatus.UNAUTHORIZED,
    )


@api_v1.exception_handler(NotFoundError)
def on_not_found_error(request, exc):
    return api_v1.create_response(
        request,
        ErrorResponse(message="Could not find the requested resource"),
        status=HTTPStatus.NOT_FOUND,
    )


@api_v1.exception_handler(FirebaseUserFacingError)
def on_firebase_user_facing_error(request, exc):
    return api_v1.create_response(
        request,
        ErrorResponse(message=str(exc)),
        status=HTTPStatus.NOT_FOUND,
    )


@api_v1.get(
    "/tags",
    response=List[str],
)
@csrf.csrf_exempt
def get_tags(request, query: str):
    # get list of relevant tags (5 max)
    return Tag.objects.filter(name__contains=query,).values_list(
        "name", flat=True
    )[:5]


@api_v1.get(
    "/csrf",
)
@csrf.csrf_exempt
@csrf.ensure_csrf_cookie
def get_csrf(request: HttpRequest):
    response = JsonResponse({"detail": "CSRF cookie set"})
    # response['X-CSRFToken'] = get_token(request)
    return response
