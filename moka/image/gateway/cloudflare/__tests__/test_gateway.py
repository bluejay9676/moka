import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from image.gateway.cloudflare.gateway import (
    CloudflareImagesAPIException,
    CloudflareImagesGateway,
)


def get_dummy_api_response(code, content, is_json=True):
    """
    Returns a dummy API response compliant with requests lib
    """
    response = MagicMock()
    response.status_code = code
    response.content = content
    if is_json:
        response.json = MagicMock(return_value=json.loads(content))

    return response


class CloudflareImageGatewayTests(TestCase):
    def setUp(self):
        self.gateway = CloudflareImagesGateway()

    def test_has_config(self):
        config = self.gateway.config
        self.assertTrue(config is not None)

    @patch("requests.post")
    def test_failed_get_upload_url(self, mock_post):
        mock_post.return_value = get_dummy_api_response(400, '{"errors": "test"}')
        self.assertRaises(
            CloudflareImagesAPIException,
            self.gateway.get_external_image_id_and_upload_url,
        )

    @patch("requests.post")
    def test_success_upload(self, mock_post):
        mock_post.return_value = get_dummy_api_response(
            200, '{"result": {"id": "test", "uploadURL": "hello.com"}}'
        )
        cf_image_id, upload_url = self.gateway.get_external_image_id_and_upload_url()
        self.assertEqual(cf_image_id, "test")
        self.assertEqual(upload_url, "hello.com")

    @patch("requests.delete")
    def test_failed_delete(self, mock_delete):
        mock_delete.return_value = get_dummy_api_response(400, "", False)
        cf_image_id = "image_id"
        self.assertRaises(
            CloudflareImagesAPIException,
            self.gateway.delete,
            cf_image_id,
        )

    @patch("requests.delete")
    def test_success_delete(self, mock_delete):
        mock_delete.return_value = get_dummy_api_response(200, "", False)
        cf_image_id = "image_id"
        self.gateway.delete(cf_image_id)

    @override_settings(CLOUDFLARE_IMAGES_ACCOUNT_HASH="account_hash")
    @override_settings(CLOUDFLARE_IMAGES_DOMAIN="hello")
    def test_get_url(self):
        name = "image_id"
        variant = "public"
        url = self.gateway.get_view_url(name, variant)
        hardcoded_url = (
            "https://hello/cdn-cgi/imagedelivery/account_hash/image_id/public"
        )
        self.assertEqual(url, hardcoded_url)

    @override_settings(
        CLOUDFLARE_IMAGES_DOMAIN="example.com",
        CLOUDFLARE_IMAGES_ACCOUNT_HASH="account_hash",
    )
    def test_get_url_with_custom_domain(self):
        name = "image_id"
        variant = "public"
        url = self.gateway.get_view_url(name, variant)
        hardcoded_url = (
            "https://example.com/cdn-cgi/imagedelivery/account_hash/image_id/public"
        )
        self.assertEqual(url, hardcoded_url)
