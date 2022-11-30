from django.http import HttpResponseForbidden
from ninja import Schema


class MokaBackendGenericError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


class NotFoundError(Exception):
    pass


class FirebaseUserFacingError(Exception):
    pass


class ErrorResponse(Schema):
    message: str


def csrf_failure(request, reason=""):
    return HttpResponseForbidden(reason)
