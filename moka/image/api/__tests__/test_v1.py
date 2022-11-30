from datetime import datetime, timedelta, timezone
from unittest import mock
from uuid import UUID

import django.test
import factory
from django.db.models import signals
from django.test import Client
from episode.factory import EpisodeFactory
from image.factory import PageFactory, ThumbnailFactory
from image.gateway.google.gateway import GoogleCloudStorageGateway
from image.models import Image, Page, Storage, Thumbnail
from moka_profile.factory import MokaProfileFactory
from series.factory import SeriesFactory


def is_valid_uuid(uuid):
    try:
        _ = UUID(uuid, version=4)
    except ValueError:
        return False
    return True


class TestImageAPI(django.test.TestCase):
    fake_upload_url = "example.com"

    def setUp(self):
        self.client = Client()
        self.mock_gcs_upload_url = mock.patch.object(
            GoogleCloudStorageGateway,
            "get_upload_url_with_external_id",
            return_value=self.fake_upload_url,
        )
        self.mock_gcs_delete = mock.patch.object(
            GoogleCloudStorageGateway,
            "delete",
            return_value=None,
        )
        self.mock_gcs_upload_url.start()
        self.addCleanup(self.mock_gcs_upload_url.stop)
        self.mock_gcs_delete.start()
        self.addCleanup(self.mock_gcs_delete.stop)

    @factory.django.mute_signals(signals.pre_delete)
    def test_new_thumbnail(self):
        profile = MokaProfileFactory()
        with mock.patch(
            "image.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ):
            response = self.client.post(
                path=f"/v1/image/thumbnail/new",
            )
            self.assertEqual(response.status_code, 200)

            response_parse = response.json()
            created_thumbnail = Thumbnail.objects.get(
                id=response_parse.get("id"),
            )
            self.assertEqual(created_thumbnail.status, Image.ImageStatus.DRAFT)
            self.assertEqual(created_thumbnail.storage, Storage.GOOGLE_CLOUD_STORAGE)
            self.assertTrue(is_valid_uuid(created_thumbnail.external_id))
            self.assertEqual(
                response_parse.get("signed_upload_url"), self.fake_upload_url
            )

    def test_cleanup(self):
        # Bulk remove - remove non-public 5+old images
        episode = EpisodeFactory()

        with mock.patch(  # To override auto_now field
            "django.utils.timezone.now",
            mock.Mock(
                return_value=datetime.now().replace(tzinfo=timezone.utc)
                - timedelta(days=20)
            ),
        ):
            public_old = ThumbnailFactory(
                status=Image.ImageStatus.PUBLIC,
            )
            not_public_old = PageFactory(
                episode=episode,
                status=Image.ImageStatus.DRAFT,
            )
            not_public_old_two = ThumbnailFactory(
                episode=episode,
                status=Image.ImageStatus.DRAFT,
            )

        public_new = PageFactory(
            episode=episode,
            status=Image.ImageStatus.PUBLIC,
            created_at=datetime.now().replace(tzinfo=timezone.utc),
        )
        not_public_new = ThumbnailFactory(
            status=Image.ImageStatus.DRAFT,
            created_at=datetime.now().replace(tzinfo=timezone.utc),
        )
        with mock.patch(
            "image.api.v1.CloudSchedulerAuthentication.authenticate",
            return_value=1,  # Arbitrary fake data
        ):
            response = self.client.post(
                path=f"/v1/image/cleanup",
                **{"HTTP_AUTHORIZATION": f"Bearer "},
            )
            self.assertEqual(response.status_code, 200)

            self.assertTrue(Thumbnail.objects.filter(id=public_old.id).exists())
            self.assertTrue(Page.objects.filter(id=public_new.id).exists())
            self.assertTrue(Thumbnail.objects.filter(id=not_public_new.id).exists())

            self.assertFalse(Page.objects.filter(id=not_public_old.id).exists())
            self.assertFalse(
                Thumbnail.objects.filter(id=not_public_old_two.id).exists()
            )

    @factory.django.mute_signals(signals.pre_delete)
    def test_new_page(self):
        series = SeriesFactory()
        episode = EpisodeFactory(series=series)
        with mock.patch(
            "image.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            response = self.client.post(
                path=f"/v1/image/page/new",
                data={"episode_id": episode.id},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

            response_parse = response.json()
            created_page = Page.objects.get(
                id=response_parse.get("id"),
            )
            self.assertEqual(created_page.status, Image.ImageStatus.DRAFT)
            self.assertEqual(created_page.storage, Storage.GOOGLE_CLOUD_STORAGE)
            self.assertEqual(created_page.episode, episode)
            self.assertTrue(is_valid_uuid(created_page.external_id))
            self.assertEqual(
                response_parse.get("signed_upload_url"), self.fake_upload_url
            )
