import datetime
from unittest import mock

import django.test
from django.test import Client
from episode.factory import EpisodeFactory
from episode.models import Episode
from image.models import Thumbnail
from moka_profile.factory import MokaProfileFactory
from series.factory import SeriesFactory
from series.models import Series


class TestNewFeed(django.test.TestCase):
    def setUp(self):
        self.client = Client()

        self.mock_signed_cookie = mock.patch.object(
            Thumbnail, "signed_cookie", return_value="test_signed_cookie"
        )
        self.mock_signed_cookie.start()
        self.addCleanup(self.mock_signed_cookie.stop)

    def test_success(self):
        tags = ["sci-fi", "adventure", "comedy"]
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC, tags=tags)
        profiles = MokaProfileFactory.create_batch(3)
        episode = EpisodeFactory(
            series=series,
            status=Episode.EpisodeStatus.PUBLIC,
            publish_date=datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
            - datetime.timedelta(hours=5),
            views=100,
            likes=[profile.id for profile in profiles],
        )

        response = self.client.get("/v1/discovery/new").json()

        self.assertEqual(response["count"], 1)
        first_item = response["items"][0]
        self.assertEqual(first_item["thumbnail_url"], "test_signed_cookie")
        self.assertEqual(first_item["episode_id"], str(episode.id))
        self.assertEqual(first_item["episode_title"], episode.title)
        self.assertEqual(first_item["artist_id"], str(series.owner.id))
        self.assertEqual(first_item["artist_name"], series.owner.display_name)
        self.assertEqual(first_item["series_id"], str(series.id))
        self.assertEqual(first_item["series_title"], series.title)

        self.assertEqual(first_item["views"], 100)
        self.assertSetEqual(set(first_item["tags"]), set(tags))
        self.assertEqual(first_item["likes"], 3)
        self.assertEqual(first_item["is_premium"], False)

    def test_draft_series(self):
        series = SeriesFactory(
            status=Series.SeriesStatus.DRAFT,
        )
        EpisodeFactory(
            series=series,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        response = self.client.get("/v1/discovery/new").json()
        self.assertEqual(response["count"], 0)

    def test_draft_episode(self):
        series = SeriesFactory(
            status=Series.SeriesStatus.PUBLIC,
        )
        EpisodeFactory(
            series=series,
            status=Episode.EpisodeStatus.DRAFT,
        )
        response = self.client.get("/v1/discovery/new").json()
        self.assertEqual(response["count"], 0)

    def test_in_order_of_publish_date(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        episode1 = EpisodeFactory(
            series=series,
            status=Episode.EpisodeStatus.PUBLIC,
            publish_date=datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
            - datetime.timedelta(hours=10),
        )
        episode2 = EpisodeFactory(
            series=series,
            status=Episode.EpisodeStatus.PUBLIC,
            publish_date=datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
            - datetime.timedelta(hours=5),
        )
        EpisodeFactory(
            series=series,
            status=Episode.EpisodeStatus.DRAFT,
        )
        response = self.client.get("/v1/discovery/new").json()

        self.assertEqual(response["count"], 2)
        first_item = response["items"][0]
        self.assertEqual(first_item["episode_id"], str(episode2.id))

        second_item = response["items"][1]
        self.assertEqual(second_item["episode_id"], str(episode1.id))

    def test_pagination(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        EpisodeFactory.create_batch(
            size=20,
            series=series,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        response = self.client.get("/v1/discovery/new?limit=5&offset=3").json()
        self.assertEqual(len(response["items"]), 5)
