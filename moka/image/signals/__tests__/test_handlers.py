from unittest import mock

import django.test
import factory
from django.db.models import signals
from django.test import Client
from episode.factory import EpisodeFactory
from image.factory import PageFactory, ThumbnailFactory
from image.gateway.cloudflare.gateway import CloudflareImagesGateway
from image.gateway.google.gateway import GoogleCloudStorageGateway
from image.models import Image, Page, Storage, Thumbnail


class TestImageSignalHandler(django.test.TestCase):
    def setUp(self):
        self.client = Client()

    def test_remove_image_source_cf(self):
        thumbnail = ThumbnailFactory(storage=Storage.CLOUDFLARE_IMAGES)
        episode = EpisodeFactory()
        page = PageFactory(episode=episode, storage=Storage.CLOUDFLARE_IMAGES)
        with mock.patch.object(
            CloudflareImagesGateway,
            "delete",
            return_value=None,
        ) as mock_cf_delete:
            thumbnail.delete()
            mock_cf_delete.assert_called_with(external_id=thumbnail.external_id)
            page.delete()
            mock_cf_delete.assert_called_with(external_id=page.external_id)

    def test_remove_image_source_gcs(self):
        thumbnail = ThumbnailFactory(storage=Storage.GOOGLE_CLOUD_STORAGE)
        episode = EpisodeFactory()
        page = PageFactory(episode=episode, storage=Storage.GOOGLE_CLOUD_STORAGE)
        with mock.patch.object(
            GoogleCloudStorageGateway,
            "delete",
            return_value=None,
        ) as mock_gcs_delete:
            thumbnail.delete()
            mock_gcs_delete.assert_called_with(external_id=thumbnail.external_id)
            page.delete()
            mock_gcs_delete.assert_called_with(external_id=page.external_id)

    @factory.django.mute_signals(signals.pre_delete)
    def test_thumbnail_change(self):
        old_thumbnail = ThumbnailFactory(status=Image.ImageStatus.PUBLIC)
        new_thumbnail = ThumbnailFactory(status=Image.ImageStatus.DRAFT)
        episode = EpisodeFactory(
            thumbnail=old_thumbnail,
        )
        episode.thumbnail = new_thumbnail

        # Check original status
        old_thumbnail_from_db = Thumbnail.objects.get(id=old_thumbnail.id)
        self.assertEqual(old_thumbnail_from_db.status, Image.ImageStatus.PUBLIC)

        episode.save()

        old_thumbnail_from_db = Thumbnail.objects.get(id=old_thumbnail.id)
        # Old thumbnail marked as removed
        self.assertEqual(old_thumbnail_from_db.status, Image.ImageStatus.REMOVED)

    def test_delete_pages(self):
        episode = EpisodeFactory()
        pages = PageFactory.create_batch(
            size=10,
            episode=episode,
            status=Image.ImageStatus.PUBLIC,
        )
        with mock.patch.object(
            GoogleCloudStorageGateway,
            "delete",
            return_value=None,
        ):
            episode.delete()

        pages = Page.objects.filter(episode=episode)
        for page in pages:
            self.assertEqual(page.status, Image.ImageStatus.REMOVED)

    def test_delete_thumbnail(self):
        thumbnail = ThumbnailFactory(status=Image.ImageStatus.DRAFT)
        episode = EpisodeFactory(
            thumbnail=thumbnail,
        )
        with mock.patch.object(
            GoogleCloudStorageGateway,
            "delete",
            return_value=None,
            new_callable=mock.PropertyMock,
        ):
            episode.delete()

        thumbnail_from_db = Thumbnail.objects.get(id=thumbnail.id)
        self.assertEqual(thumbnail_from_db.status, Image.ImageStatus.REMOVED)
