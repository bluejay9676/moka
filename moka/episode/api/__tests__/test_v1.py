# import random
import datetime
from unittest import mock

import django.test
from django.test import Client
from episode.api.schema import EpisodeFetchStatus, EpisodeSchema
from episode.factory import EpisodeFactory
from episode.models import Episode, PurchaseEpisode
from image.factory import PageFactory, ThumbnailFactory
from image.models import Image, Page, Thumbnail
from moka_profile.factory import MokaProfileFactory
from series.factory import SeriesFactory
from series.models import Series


class TestEpisodeAPI(django.test.TestCase):
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

    def test_next_episode(self):
        series = SeriesFactory()
        episode = EpisodeFactory(
            series=series,
            episode_number=10,
        )
        # No next episode
        response = self.client.get(f"/v1/episode/{episode.id}/next")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json())

        # Some
        EpisodeFactory(
            series=series,
            episode_number=11,
            status=Episode.EpisodeStatus.DRAFT,
        )
        EpisodeFactory(
            series=series,
            episode_number=13,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        next_public_episode = EpisodeFactory(
            series=series,
            episode_number=12,
            status=Episode.EpisodeStatus.PUBLIC,
        )

        response = self.client.get(f"/v1/episode/{episode.id}/next")
        response_parsed = EpisodeSchema.parse_obj(response.json())
        self.assertEqual(response_parsed.metadata.id, str(next_public_episode.id))
        # Next and Prev always called with NEED_PURCHASE level
        self.assertEqual(response_parsed.fetch_status, EpisodeFetchStatus.NEED_PURCHASE)

    def test_prev_episode(self):
        series = SeriesFactory()
        episode = EpisodeFactory(
            series=series,
            episode_number=10,
        )
        # No prev episode
        response = self.client.get(f"/v1/episode/{episode.id}/prev")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json())

        # Some
        EpisodeFactory(
            series=series,
            episode_number=9,
            status=Episode.EpisodeStatus.DRAFT,
        )
        EpisodeFactory(
            series=series,
            episode_number=1,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        prev_public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
        )

        response = self.client.get(f"/v1/episode/{episode.id}/prev")
        response_parsed = EpisodeSchema.parse_obj(response.json())
        self.assertEqual(response_parsed.metadata.id, str(prev_public_episode.id))
        # Next and Prev always called with NEED_PURCHASE level
        self.assertEqual(response_parsed.fetch_status, EpisodeFetchStatus.NEED_PURCHASE)

    def test_get_public_episode(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        response = self.client.get(f"/v1/episode/{public_episode.id}/public")
        response_parsed = EpisodeSchema.parse_obj(response.json())
        self.assertEqual(response_parsed.metadata.id, str(public_episode.id))
        self.assertEqual(response_parsed.metadata.is_owner, False)
        self.assertEqual(response_parsed.fetch_status, EpisodeFetchStatus.ACCESSIBLE)

    def test_get_public_episode_series_not_public(self):
        series = SeriesFactory(status=Series.SeriesStatus.DRAFT)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        response = self.client.get(f"/v1/episode/{public_episode.id}/public")
        self.assertEqual(response.status_code, 404)

    def test_get_public_episode_authorized(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        with mock.patch(
            "episode.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=series.owner,
        ) as mock_auth:
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            mock_auth.assert_called()
            response_parsed = EpisodeSchema.parse_obj(response.json())
            self.assertEqual(response_parsed.metadata.id, str(public_episode.id))
            self.assertEqual(response_parsed.metadata.is_owner, True)
            self.assertEqual(
                response_parsed.fetch_status, EpisodeFetchStatus.ACCESSIBLE
            )

    def test_get_public_episode_premium_purhcased(self):
        non_owner = MokaProfileFactory()
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
            is_premium=True,
        )
        PurchaseEpisode.objects.create(
            episode=public_episode,
            profile=non_owner,
        )
        with mock.patch(
            "episode.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=non_owner,
        ) as mock_auth:
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            mock_auth.assert_called()
            response_parsed = EpisodeSchema.parse_obj(response.json())
            self.assertEqual(response_parsed.metadata.id, str(public_episode.id))
            self.assertEqual(response_parsed.metadata.is_owner, False)
            self.assertEqual(
                response_parsed.fetch_status, EpisodeFetchStatus.ACCESSIBLE
            )

    def test_get_public_episode_premium_owner(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
            is_premium=True,
        )
        with mock.patch(
            "episode.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=series.owner,
        ) as mock_auth:
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            mock_auth.assert_called()
            response_parsed = EpisodeSchema.parse_obj(response.json())
            self.assertEqual(response_parsed.metadata.id, str(public_episode.id))
            self.assertEqual(response_parsed.metadata.is_owner, True)
            self.assertEqual(
                response_parsed.fetch_status, EpisodeFetchStatus.ACCESSIBLE
            )

    def test_get_public_episode_premium_not_authenticated(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
            is_premium=True,
        )
        with mock.patch(
            "episode.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=1,
        ):
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["pages"]), 0)
            self.assertEqual(
                response.json()["fetch_status"], EpisodeFetchStatus.NEED_PURCHASE
            )

    def test_get_public_episode_premium_not_purchased_not_owner(self):
        non_owner = MokaProfileFactory()
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
            is_premium=True,
            price=10,
        )
        with mock.patch(
            "episode.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=non_owner,
        ) as mock_auth:
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            mock_auth.assert_called()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()["pages"]), 0)
            self.assertEqual(
                response.json()["fetch_status"], EpisodeFetchStatus.NEED_PURCHASE
            )

    def test_get_public_episode_prerelease_purhcased(self):
        non_owner = MokaProfileFactory()
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PRE_RELEASE,
        )
        PurchaseEpisode.objects.create(
            episode=public_episode,
            profile=non_owner,
        )
        with mock.patch(
            "episode.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=non_owner,
        ) as mock_auth:
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            mock_auth.assert_called()
            response_parsed = EpisodeSchema.parse_obj(response.json())
            self.assertEqual(response_parsed.metadata.id, str(public_episode.id))
            self.assertEqual(response_parsed.metadata.is_owner, False)
            self.assertEqual(
                response_parsed.fetch_status, EpisodeFetchStatus.ACCESSIBLE
            )

    def test_get_public_episode_prerelease_owner(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PRE_RELEASE,
        )
        with mock.patch(
            "episode.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=series.owner,
        ) as mock_auth:
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            mock_auth.assert_called()
            response_parsed = EpisodeSchema.parse_obj(response.json())
            self.assertEqual(response_parsed.metadata.id, str(public_episode.id))
            self.assertEqual(response_parsed.metadata.is_owner, True)
            self.assertEqual(
                response_parsed.fetch_status, EpisodeFetchStatus.ACCESSIBLE
            )

    def test_get_public_episode_liked(self):
        profile = MokaProfileFactory()
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        public_episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        with mock.patch(
            "episode.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=profile,
        ) as mock_auth, mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ):
            # Assert before like
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            mock_auth.assert_called()
            response_parsed = EpisodeSchema.parse_obj(response.json())
            self.assertEqual(response_parsed.metadata.id, str(public_episode.id))
            self.assertEqual(response_parsed.metadata.is_owner, False)
            self.assertEqual(response_parsed.metadata.is_liked, False)

            # Like
            response = self.client.post(
                path=f"/v1/episode/{public_episode.id}/like",
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            episode_from_db = Episode.objects.get(id=public_episode.id)
            self.assertTrue(episode_from_db.is_liked_by(profile))

            # After like
            response = self.client.get(
                f"/v1/episode/{public_episode.id}/public",
                content_type="application/json",
            )
            response_parsed = EpisodeSchema.parse_obj(response.json())
            self.assertEqual(response_parsed.metadata.id, str(public_episode.id))
            self.assertEqual(response_parsed.metadata.is_owner, False)
            self.assertEqual(response_parsed.metadata.is_liked, True)

    def test_get_episode(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.DRAFT,
        )
        response = self.client.get(f"/v1/episode/{episode.id}")
        self.assertEqual(response.status_code, 401)

        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ) as mock_auth:
            response = self.client.get(
                f"/v1/episode/{episode.id}",
                content_type="application/json",
            )
            mock_auth.assert_called()
            response_parsed = EpisodeSchema.parse_obj(response.json())
            self.assertEqual(response_parsed.metadata.id, str(episode.id))
            self.assertEqual(response_parsed.metadata.is_owner, True)

    def test_edit_episode(self):
        series = SeriesFactory()
        episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.DRAFT,
        )
        thumbnail = ThumbnailFactory()
        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            response = self.client.post(
                path=f"/v1/episode/{episode.id}/edit",
                data={
                    "thumbnail_id": thumbnail.id,
                    "title": "Hello",
                    "new_page_ordering": [],
                },
                content_type="application/json",
            ).json()
            self.assertEqual(response["id"], str(episode.id))
            self.assertEqual(response["title"], "Hello")

            episode_from_db = Episode.objects.get(id=episode.id)
            self.assertEqual(episode_from_db.status, Episode.EpisodeStatus.PUBLIC)
            self.assertEqual(episode_from_db.thumbnail, thumbnail)

    def test_register_scheduled_release(self):
        series = SeriesFactory()
        episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.DRAFT,
        )
        thumbnail = ThumbnailFactory()
        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            release_date = datetime.datetime.now().replace(
                tzinfo=datetime.timezone.utc
            ) + datetime.timedelta(days=10)
            response = self.client.post(
                path=f"/v1/episode/{episode.id}/edit",
                data={
                    "thumbnail_id": thumbnail.id,
                    "title": "Hello",
                    "new_page_ordering": [],
                    "release_scheduled_date": release_date.isoformat(),
                },
                content_type="application/json",
            ).json()
            self.assertEqual(response["id"], str(episode.id))
            self.assertEqual(response["title"], "Hello")

            episode_from_db = Episode.objects.get(id=episode.id)
            self.assertEqual(episode_from_db.status, Episode.EpisodeStatus.PRE_RELEASE)
            self.assertEqual(episode_from_db.release_scheduled_date, release_date)
            self.assertEqual(episode_from_db.publish_date, release_date)
            self.assertEqual(episode_from_db.thumbnail, thumbnail)

    def test_already_public_invalid_scheduled_release(self):
        series = SeriesFactory()
        episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        thumbnail = ThumbnailFactory()
        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            release_date = datetime.datetime.now().replace(
                tzinfo=datetime.timezone.utc
            ) + datetime.timedelta(days=10)
            response = self.client.post(
                path=f"/v1/episode/{episode.id}/edit",
                data={
                    "thumbnail_id": thumbnail.id,
                    "title": "Hello",
                    "new_page_ordering": [],
                    "release_scheduled_date": release_date.isoformat(),
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

    def test_already_public_valid_scheduled_release(self):
        series = SeriesFactory()
        episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.PUBLIC,
        )
        thumbnail = ThumbnailFactory()
        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            release_date = datetime.datetime.now().replace(
                tzinfo=datetime.timezone.utc
            ) - datetime.timedelta(days=10)
            response = self.client.post(
                path=f"/v1/episode/{episode.id}/edit",
                data={
                    "thumbnail_id": thumbnail.id,
                    "title": "Hello",
                    "new_page_ordering": [],
                    "release_scheduled_date": release_date.isoformat(),
                },
                content_type="application/json",
            ).json()
            self.assertEqual(response["id"], str(episode.id))
            self.assertEqual(response["title"], "Hello")

            episode_from_db = Episode.objects.get(id=episode.id)
            self.assertEqual(episode_from_db.status, Episode.EpisodeStatus.PUBLIC)
            self.assertEqual(episode_from_db.release_scheduled_date, None)
            # Publish date not changed
            self.assertEqual(episode_from_db.publish_date, episode.publish_date)
            self.assertEqual(episode_from_db.thumbnail, thumbnail)

    def test_edit_episode_non_owner(self):
        non_owner = MokaProfileFactory()
        series = SeriesFactory()
        episode = EpisodeFactory(
            series=series,
            episode_number=8,
            status=Episode.EpisodeStatus.DRAFT,
        )
        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate", return_value=non_owner
        ):
            response = self.client.post(
                path=f"/v1/episode/{episode.id}/edit",
                data={
                    "thumbnail_id": 0,
                    "title": "Hello",
                    "status": "PUBLIC",
                    "new_page_ordering": [],
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)

    def test_pages_change_non_owner(self):
        non_owner = MokaProfileFactory()
        episode = EpisodeFactory()
        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate", return_value=non_owner
        ):
            response = self.client.post(
                path=f"/v1/episode/{episode.id}/edit",
                data={
                    "title": "Hello",
                    "status": "PUBLIC",
                    "new_page_ordering": [],
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)

    def test_pages_change(self):
        # Generate original episode and pages
        episode = EpisodeFactory()
        original_pages = []
        for i in range(10):
            original_pages.append(
                PageFactory(
                    episode=episode, order=i + 1, status=Image.ImageStatus.PUBLIC
                )
            )

        # Create new page ordering
        # some pages order changed
        new_page_ordering = [original_pages[2], original_pages[5]]
        # some pages new added
        added_page = PageFactory(episode=episode, status=Image.ImageStatus.DRAFT)
        new_page_ordering.append(added_page)
        # some pages removed

        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=episode.series.owner,
        ):
            response = self.client.post(
                path=f"/v1/episode/{episode.id}/edit",
                data={
                    "title": "Hello",
                    "status": "PUBLIC",
                    "new_page_ordering": [
                        {"id": page.id, "random_key": "123"}
                        for page in new_page_ordering
                    ],
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

            # Assert
            episode_from_db = Episode.objects.get(id=episode.id)
            pages = episode_from_db.pages.exclude(
                status=Episode.EpisodeStatus.REMOVED
            ).order_by("order")

            # get episode reflects this change
            # saved pages are public
            self.assertEqual(len(pages), 3)
            self.assertEqual(pages[0].id, original_pages[2].id)
            self.assertEqual(pages[0].order, 1)
            self.assertEqual(pages[0].status, Image.ImageStatus.PUBLIC)
            self.assertEqual(pages[1].id, original_pages[5].id)
            self.assertEqual(pages[1].order, 2)
            self.assertEqual(pages[1].status, Image.ImageStatus.PUBLIC)
            self.assertEqual(pages[2].id, added_page.id)
            self.assertEqual(pages[2].order, 3)
            self.assertEqual(pages[2].status, Image.ImageStatus.PUBLIC)

            # removed ones are marked as removed
            for page in original_pages:
                if page.id not in [
                    original_pages[2].id,
                    original_pages[5].id,
                    added_page.id,
                ]:
                    page_from_db = Page.objects.get(id=page.id)
                    self.assertEqual(page_from_db.status, Image.ImageStatus.REMOVED)

    def test_new_draft_episode(self):
        series = SeriesFactory()
        EpisodeFactory.create_batch(size=10, series=series)
        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            # Reorder all
            response = self.client.post(
                path=f"/v1/episode/new",
                data={
                    "series_id": series.id,
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

            parsed_response = response.json()
            created_episode = Episode.objects.get(id=parsed_response["metadata"]["id"])
            self.assertEqual(created_episode.status, Series.SeriesStatus.DRAFT)
            self.assertEqual(created_episode.series, series)

            # episode number largest out of all episodes
            self.assertEqual(
                created_episode.id,
                series.episodes.order_by("-episode_number")[0].id,
            )

    def test_episode_delete(self):
        # delete episode - episode numbers are resorted
        series = SeriesFactory()
        episodes = []

        for i in range(10):
            episodes.append(
                EpisodeFactory(
                    series=series,
                    episode_number=i + 1,
                )
            )

        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            response = self.client.post(
                path=f"/v1/episode/{episodes[3].id}/delete",
            )
            self.assertEqual(response.status_code, 200)

            # Assert
            episodes_from_db = Episode.objects.filter(series=series).order_by(
                "episode_number"
            )
            self.assertEqual(len(episodes_from_db), 9)
            for i in range(9):
                self.assertEqual(episodes_from_db[i].episode_number, i + 1)

    def test_like(self):
        series = SeriesFactory()
        episode1 = EpisodeFactory(
            series=series,
            episode_number=10,
        )
        episode2 = EpisodeFactory(
            series=series,
            episode_number=11,
        )
        with mock.patch(
            "episode.api.v1.FirebaseAuthentication.authenticate",
            return_value=series.owner,
        ):
            self.assertEqual(series.owner.liked_episodes.count(), 0)
            self.assertEqual(episode1.get_likes(), 0)
            self.assertEqual(episode2.get_likes(), 0)

            # Reorder all
            response = self.client.post(
                path=f"/v1/episode/{episode1.id}/like",
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

            # Check from profile
            self.assertEqual(series.owner.liked_episodes.count(), 1)
            self.assertEqual(series.owner.liked_episodes.first(), episode1)

            # Check from episode
            self.assertEqual(episode1.get_likes(), 1)
            self.assertEqual(episode2.get_likes(), 0)
            self.assertEqual(episode1.likes.first(), series.owner)

    def test_sync_views_and_update_trend_score(self):
        series = SeriesFactory(status=Series.SeriesStatus.PUBLIC)
        episodes = EpisodeFactory.create_batch(
            size=10,
            views=0,
            status=Episode.EpisodeStatus.PUBLIC,
            series=series,
            publish_date=datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
            - datetime.timedelta(days=1),
        )
        for i, episode in enumerate(episodes):
            for _ in range(i):
                episode.incr_view()
            self.assertEqual(episode.views, 0)
            self.assertEqual(episode.trend_score, 0)

        with mock.patch(
            "image.api.v1.CloudSchedulerAuthentication.authenticate",
            return_value=1,  # Arbitrary fake data
        ):
            response = self.client.post(
                path=f"/v1/episode/view-sync-and-update-trend-score",
                **{"HTTP_AUTHORIZATION": f"Bearer "},
            )
            self.assertEqual(response.status_code, 200)

        for i, episode in enumerate(episodes):
            episode.refresh_from_db()
            self.assertEqual(episode.views, i)
            self.assertEqual(episode.trend_score, i * 1.0)
            self.assertEqual(episode.get_buffer_views(), 0)

    def test_scheduled_release(self):
        release_date = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        episodes = EpisodeFactory.create_batch(
            size=10,
            status=Episode.EpisodeStatus.PRE_RELEASE,
            release_scheduled_date=release_date,
        )

        with mock.patch(
            "image.api.v1.CloudSchedulerAuthentication.authenticate",
            return_value=1,  # Arbitrary fake data
        ):
            response = self.client.post(
                path=f"/v1/episode/publish-episodes",
                **{"HTTP_AUTHORIZATION": f"Bearer "},
            )
            self.assertEqual(response.status_code, 200)

        for episode in episodes:
            episode.refresh_from_db()
            self.assertEqual(episode.status, Episode.EpisodeStatus.PUBLIC)
            self.assertEqual(episode.publish_date, release_date)
