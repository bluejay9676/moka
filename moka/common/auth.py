import json

from common.logger import StructuredLogger
from django.http import HttpRequest
from firebase_admin.auth import InvalidSessionCookieError, verify_session_cookie
from google.auth.transport import requests
from google.oauth2 import id_token
from moka_profile.models import MokaProfile
from ninja.security import APIKeyCookie, HttpBearer

logger = StructuredLogger(__name__)


class UnavailableCookieRedirectLogin(Exception):
    pass


class InvalidFirebaseToken(Exception):
    pass


class FirebaseUserNotFoundError(Exception):
    pass


class NoMatchingProfile(Exception):
    pass


class CloudSchedulerAuthentication(HttpBearer):
    def authenticate(self, request, token):
        # https://stackoverflow.com/questions/53181297/verify-http-request-from-google-cloud-scheduler
        # https://developers.google.com/identity/sign-in/web/backend-auth
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
        )
        logger.info(
            event_name="CLOUD_SCHEDULER_AUTHENTICATION",
            msg=json.dumps(idinfo),
        )

        if (
            idinfo["email"]
            != "moka-scheduler@cosmic-quarter-343904.iam.gserviceaccount.com"
        ):
            return None

        if idinfo["iss"] not in ["https://accounts.google.com"]:
            return None
        return True


class FirebaseAuthentication(APIKeyCookie):
    """
    You can check custom claims to confirm user is an admin.
    if decoded_claims.get('admin') is True:
        return serve_content_for_admin(decoded_claims)
    """

    param_name: str = "session"

    def authenticate(self, request: HttpRequest, key):
        session_cookie = key
        if session_cookie is not None:
            try:
                decoded_claims = verify_session_cookie(
                    session_cookie, check_revoked=True
                )
                firebase_uid = decoded_claims["sub"]
                return MokaProfile.objects.get(firebase_uid=firebase_uid)
            except MokaProfile.DoesNotExist:
                raise NoMatchingProfile
            except InvalidSessionCookieError:
                # Session cookie is invalid, expired or revoked. Force user to login.
                raise UnavailableCookieRedirectLogin
        return None


class FirebaseOptionalAuthentication(APIKeyCookie):
    param_name: str = "session"

    def authenticate(self, request: HttpRequest, key):
        session_cookie = key
        if session_cookie is not None:
            try:
                decoded_claims = verify_session_cookie(
                    session_cookie, check_revoked=True
                )
                firebase_uid = decoded_claims["sub"]
                return MokaProfile.objects.get(firebase_uid=firebase_uid)
            except MokaProfile.DoesNotExist:
                return 1
            except InvalidSessionCookieError:
                return 1
        return 1
