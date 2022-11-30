# import datetime
import base64
import datetime
import hashlib
import hmac

import google.auth
from django.conf import settings
from google.auth.transport import requests
from google.cloud import storage
from image.gateway.gateway import ImageStorageGateway
from image.gateway.google.config import Config
from six.moves import urllib


class GoogleCloudStorageGateway(ImageStorageGateway):
    def __init__(self, **kwargs):
        self.config = Config()
        if settings.SYSTEM_ENV == "prod":
            self.credentials, _project_id = google.auth.default()
            self.credentials.refresh(requests.Request())
            self.client = storage.Client()
        else:
            self.credentials = settings.GS_CREDENTIALS
            self.client = storage.Client(
                credentials=self.credentials,
            )

    def __sign_url(
        self,
        url,
    ):
        stripped_url = url.strip()
        parsed_url = urllib.parse.urlsplit(stripped_url)
        query_params = urllib.parse.parse_qs(parsed_url.query, keep_blank_values=True)
        epoch = datetime.datetime.utcfromtimestamp(0)
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        expiration_timestamp = int((expiration_time - epoch).total_seconds())
        decoded_key = base64.urlsafe_b64decode(self.config.signing_key)

        url_pattern = "{url}{separator}Expires={expires}&KeyName={key_name}"

        url_to_sign = url_pattern.format(
            url=stripped_url,
            separator="&" if query_params else "?",
            expires=expiration_timestamp,
            key_name=self.config.signing_key_name,
        )

        digest = hmac.new(
            decoded_key, url_to_sign.encode("utf-8"), hashlib.sha1
        ).digest()
        signature = base64.urlsafe_b64encode(digest).decode("utf-8")

        return "{url}&Signature={signature}".format(
            url=url_to_sign, signature=signature
        )

    def get_upload_url_with_external_id(self, external_id: str):
        """Generates a v4 signed URL for uploading a blob using HTTP PUT.

        Note that this method requires a service account key file. You can not use
        this if you are using Application Default Credentials from Google Compute
        Engine or from the Google Cloud SDK.

        image input is an image object from image.models.Image

        "curl -X PUT -H 'Content-Type: application/octet-stream' "
        "--upload-file my-file generate-signed-url"
        """
        bucket = self.client.bucket(self.config.bucket_name)
        blob = bucket.blob(external_id)  # external_id as blob_name

        url = blob.generate_signed_url(
            version="v4",
            # This URL is valid for 15 minutes
            expiration=datetime.timedelta(minutes=15),
            # Allow PUT requests using this URL.
            method="PUT",
            service_account_email=self.credentials.service_account_email,
            access_token=self.credentials.token,
        )
        return url

    def get_view_url(self, external_id: str, variant_name: str = None):
        return self.__sign_url(f"{self.config.cdn_hostname}/{external_id}")

    def delete(self, external_id):
        bucket = self.client.bucket(self.config.bucket_name)
        blob = bucket.blob(external_id)  # external_id as blob_name
        blob.delete()
