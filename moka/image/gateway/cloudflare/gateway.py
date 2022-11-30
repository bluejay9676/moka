import requests
from image.gateway.cloudflare.config import Config
from image.gateway.gateway import ImageStorageGateway


class CloudflareImagesAPIException(Exception):
    """
    Exception raised by Cloudflare Images API
    """

    pass


class CloudflareImagesGateway(ImageStorageGateway):
    def __init__(self, **kwargs):
        self.config = Config()

    def get_external_image_id_and_upload_url(self):
        """
        https://developers.cloudflare.com/images/cloudflare-images/upload-images/direct-creator-upload/
        """
        url = "https://api.cloudflare.com/client/v4/accounts/{}/images/v2/direct_upload".format(
            self.config.account_id,
        )

        headers = {"Authorization": "Bearer {}".format(self.config.api_token)}

        response = requests.post(url, headers=headers, data={})

        status_code = response.status_code
        if status_code != 200:
            raise CloudflareImagesAPIException(str(response.text))

        response_body = response.json()
        external_id = response_body.get("result").get("id")
        upload_url = response_body.get("result").get("uploadURL")
        return external_id, upload_url

    def get_view_url(self, external_id, variant_name):
        if self.config.domain:
            return "https://{}/cdn-cgi/imagedelivery/{}/{}/{}".format(
                self.config.domain,
                self.config.account_hash,
                external_id,
                variant_name,
            )

        return "https://imagedelivery.net/{}/{}/{}".format(
            self.config.account_hash,
            external_id,
            variant_name,
        )

    def delete(self, external_id):
        """
        Deletes a file if it exists, otherwise raise an exception
        """

        url = "https://api.cloudflare.com/client/v4/accounts/{}/images/v1/{}".format(
            self.config.account_id, external_id
        )

        headers = {"Authorization": "Bearer {}".format(self.config.api_token)}

        response = requests.delete(url, headers=headers)

        status_code = response.status_code
        if status_code != 200:
            raise CloudflareImagesAPIException(str(response.text))
