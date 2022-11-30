import random
from unittest import mock

import django.test
from django.test import Client
from episode.factory import EpisodeFactory
from episode.models import Episode
from image.factory import ThumbnailFactory
from image.models import Thumbnail
from moka_profile.factory import MokaProfileFactory
from series.api.schema import SeriesMetaDataSchema
from series.factory import SeriesFactory
from series.models import Series


class TestSeriesAPI(django.test.TestCase):
    fake_signed_cookie = "test_signed_cookie"

    def setUp(self):
        self.client = Client()

        self.mock_signed_cookie = mock.patch.object(
            Thumbnail,
            "signed_cookie",
            return_value=self.fake_signed_cookie,
            new_callable=mock.PropertyMock,
        )
        self.mock_signed_cookie.start()
        self.addCleanup(self.mock_signed_cookie.stop)

    def test_get_series(self):
        tags = ["sci-fi", "adventure", "comedy"]
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC, tags=tags)
        response = self.client.get(f"/v1/series/{series.id}")
        response_parsed = SeriesMetaDataSchema.parse_obj(response.json())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_parsed.thumbnail_url, self.fake_signed_cookie)
        self.assertFalse(response_parsed.is_owner)

    def test_get_all_series_episodes_in_order(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        episode1 = EpisodeFactory(
            series=series,
            status=Episode.EpisodeStatus.PUBLIC,
            episode_number=1,
        )
        episode2 = EpisodeFactory(
            series=series, status=Episode.EpisodeStatus.DRAFT, episode_number=2
        )
        EpisodeFactory(
            series=series,
            status=Episode.EpisodeStatus.REMOVED,
        )
        EpisodeFactory(  # Different series
            status=Episode.EpisodeStatus.DRAFT,
        )
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            response = self.client.get(
                f"/v1/series/{series.id}/episodes/all",
            ).json()

            self.assertEqual(response["count"], 2)
            first_item = response["items"][0]
            second_item = response["items"][1]
            self.assertEqual(first_item["id"], str(episode2.id))
            self.assertEqual(second_item["id"], str(episode1.id))

    def test_get_all_series_episodes_in_order_unauthorized(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate", return_value=None
        ):
            response = self.client.get(
                f"/v1/series/{series.id}/episodes/all",
            )
            self.assertEqual(response.status_code, 401)

    def test_edit_series_unauthorized(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate", return_value=None
        ):
            response = self.client.post(
                path=f"/v1/series/{series.id}/edit",
            )
            self.assertEqual(response.status_code, 401)

    def test_edit_series_non_owner(self):
        non_owner = MokaProfileFactory()
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate", return_value=non_owner
        ):
            response = self.client.post(
                path=f"/v1/series/{series.id}/edit",
                data={
                    "title": "New Title",
                    "description": "New Description",
                    "status": Series.SeriesStatus.PUBLIC,
                    "tags": ["world", "hello"],
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)

    def test_edit_series_no_thumbnail(self):
        series = SeriesFactory(status=Series.SeriesStatus.DRAFT)
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            response = self.client.post(
                path=f"/v1/series/{series.id}/edit",
                data={
                    "title": "New Title",
                    "description": "New Description",
                    "status": Series.SeriesStatus.PUBLIC,
                    "tags": ["world", "hello"],
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

            # retrieve Series and check values updated
            new_series = Series.objects.get(id=series.id)
            self.assertIsNone(new_series.thumbnail)

    def test_edit_series(self):
        new_thumbnail = ThumbnailFactory()
        series = SeriesFactory(status=Series.SeriesStatus.DRAFT)
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            response = self.client.post(
                path=f"/v1/series/{series.id}/edit",
                data={
                    "thumbnail_id": str(new_thumbnail.id),
                    "title": "New Title",
                    "description": "New Description",
                    "status": Series.SeriesStatus.PUBLIC,
                    "tags": ["world", "hello", "1", "2", "3", "4", "5"],
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

            # retrieve Series and check values updated
            new_series = Series.objects.get(id=series.id)
            self.assertEqual(new_series.thumbnail.id, new_thumbnail.id)
            self.assertEqual(new_series.title, "New Title")
            self.assertEqual(new_series.status, Series.SeriesStatus.PUBLIC)
            # Publish date got updated
            self.assertTrue(new_series.publish_date > series.publish_date)
            self.assertTrue(new_series.get_tags(), ["world", "hello", "1", "2", "3"])

    def test_edit_series_episode_order_unauthorized(self):
        series = SeriesFactory()
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate", return_value=None
        ):
            response = self.client.post(
                path=f"/v1/series/{series.id}/episode/edit",
            )
            self.assertEqual(response.status_code, 401)

    def test_edit_series_episode_order_non_owner(self):
        non_owner = MokaProfileFactory()
        series = SeriesFactory()
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate", return_value=non_owner
        ):
            response = self.client.post(
                path=f"/v1/series/{series.id}/episode/edit",
                data={
                    "start": 0,
                    "end": 10,
                    "new_episode_ordering": [],
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)

    def test_edit_series_episode_order(self):
        series = SeriesFactory()
        EpisodeFactory.create_batch(
            size=5,
            series=series,
            status=Episode.EpisodeStatus.PUBLIC,
        )

        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            original_order = list(
                series.episodes.order_by("episode_number").values(
                    "id", "episode_number"
                )
            )
            new_order = original_order.copy()
            random.shuffle(new_order)

            # Reorder all
            response = self.client.post(
                path=f"/v1/series/{series.id}/episode/edit",
                data={
                    "start": original_order[0]["episode_number"],
                    "end": original_order[-1]["episode_number"],
                    "new_episode_ordering": new_order,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            check_db_series = Series.objects.get(id=series.id)
            check_db_update = list(
                check_db_series.episodes.order_by("episode_number").values(
                    "id", "episode_number"
                )
            )
            for idx, obj in enumerate(check_db_update):
                self.assertEqual(obj["id"], new_order[idx]["id"])
            self.assertEqual(
                check_db_update[0]["episode_number"],
                original_order[0]["episode_number"],
            )
            self.assertEqual(
                check_db_update[-1]["episode_number"],
                original_order[-1]["episode_number"],
            )

    def test_new_draft_series(self):
        caller = MokaProfileFactory()
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate", return_value=caller
        ):
            # Reorder all
            response = self.client.post(
                path=f"/v1/series/new",
            )
            self.assertEqual(response.status_code, 200)

            parsed_response = response.json()
            self.assertEqual(parsed_response["artist_id"], str(caller.id))
            self.assertTrue(parsed_response["is_owner"])
            created_series = Series.objects.get(id=parsed_response["series_id"])
            self.assertEqual(created_series.status, Series.SeriesStatus.DRAFT)
            self.assertEqual(created_series.owner.id, caller.id)

    def test_delete_series(self):
        series = SeriesFactory()
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            response = self.client.post(
                path=f"/v1/series/{series.id}/delete",
            )
            self.assertEqual(response.status_code, 200)

    def test_delete_series_non_owner(self):
        non_owner = MokaProfileFactory()
        series = SeriesFactory()
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate", return_value=non_owner
        ):
            response = self.client.post(
                path=f"/v1/series/{series.id}/delete",
            )
            self.assertEqual(response.status_code, 401)

    def test_delete_non_existent_series(self):
        caller = MokaProfileFactory()
        with mock.patch(
            "series.api.v1.FirebaseAuthentication.authenticate", return_value=caller
        ):
            response = self.client.post(
                path=f"/v1/series/{99999999999}/delete",
            )
            self.assertEqual(response.status_code, 404)
