# import random
from unittest import mock

import django.test
from django.test import Client

# from episode.factory import EpisodeFactory
# from episode.models import Episode
from image.factory import ThumbnailFactory
from image.models import Thumbnail
from moka_profile.api.schema import ProfileSchema
from moka_profile.factory import MokaProfileFactory
from moka_profile.models import MokaProfile

# from series.api.schema import SeriesMetaDataSchema
from series.factory import SeriesFactory
from series.models import Series


class TestProfileAPI(django.test.TestCase):
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

    def test_get_profile(self):
        thumbnail = ThumbnailFactory()
        profile = MokaProfileFactory(thumbnail=thumbnail)
        response = self.client.get(f"/v1/profile/{profile.id}")
        response_parsed = ProfileSchema.parse_obj(response.json())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_parsed.profile_picture_url, self.fake_signed_cookie)
        self.assertEqual(response_parsed.id, str(profile.id))
        self.assertFalse(response_parsed.is_owner)
        self.assertEqual(response_parsed.followers, 0)
        self.assertEqual(response_parsed.following, 0)

    def test_get_profile_with_auth(self):
        thumbnail = ThumbnailFactory()
        profile = MokaProfileFactory(thumbnail=thumbnail)

        with mock.patch(
            "moka_profile.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=profile,
        ) as mock_auth:
            response = self.client.get(path=f"/v1/profile/{profile.id}")
            mock_auth.assert_called()
            response_parsed = ProfileSchema.parse_obj(response.json())
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response_parsed.is_owner)

    def test_get_works(self):
        profile = MokaProfileFactory()
        SeriesFactory.create_batch(
            size=10,
            owner=profile,
            status=Series.SeriesStatus.PUBLIC,
        )
        SeriesFactory.create_batch(
            size=5,
            owner=profile,
            status=Series.SeriesStatus.DRAFT,
        )
        SeriesFactory.create_batch(
            size=3,
            owner=profile,
            status=Series.SeriesStatus.REMOVED,
        )

        # Get only public
        response = self.client.get(
            path=f"/v1/profile/{profile.id}/works",
        ).json()
        self.assertEqual(response["count"], 10)

        # Get all except removed
        with mock.patch(
            "moka_profile.api.v1.FirebaseOptionalAuthentication.authenticate",
            return_value=profile,
        ):
            response = self.client.get(
                path=f"/v1/profile/{profile.id}/works",
            ).json()
            self.assertEqual(response["count"], 15)

    def test_edit_profile_non_owner(self):
        profile = MokaProfileFactory()
        other_profile = MokaProfileFactory()
        with mock.patch(
            "moka_profile.api.v1.FirebaseAuthentication.authenticate",
            return_value=other_profile,
        ):
            response = self.client.post(
                path=f"/v1/profile/{profile.id}/edit",
                data={},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)

    def test_edit_profile(self):
        new_thumbnail = ThumbnailFactory()
        profile = MokaProfileFactory()
        with mock.patch(
            "moka_profile.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ), mock.patch(
            "firebase_admin.auth.update_user",
            return_value=None,
        ) as firebase_call:
            response = self.client.post(
                path=f"/v1/profile/{profile.id}/edit",
                data={
                    "thumbnail_id": str(new_thumbnail.id),
                    "display_name": "Mocha",
                    "description": "Hello",
                },
                content_type="application/json",
            )
            firebase_call.assert_called_with(
                uid=profile.firebase_uid,
                photo_url=new_thumbnail.signed_cookie,
                display_name="Mocha",
            )
            self.assertEqual(response.status_code, 200)

    def test_new_profile(self):
        mock_user = mock.Mock()
        mock_user.uid = "test_firebase_uid1234"

        with mock.patch(
            "firebase_admin.auth.create_user",
            return_value=mock_user,
        ) as firebase_create_user, mock.patch(
            "firebase_admin.auth.update_user",
            return_value=mock_user,
        ) as firebase_update_user:
            response = self.client.post(
                path=f"/v1/profile/new",
                data={
                    "email": "test@test.com",
                    "password": "test_password",
                    "username": "tester",
                },
                content_type="application/json",
            )
            firebase_create_user.assert_called_with(
                email="test@test.com",
                email_verified=False,
                display_name="tester",
                disabled=False,
            )
            firebase_update_user.assert_called_with(
                uid=mock_user.uid,
                password="test_password",
            )
            self.assertEqual(response.status_code, 200)
            created_profile = MokaProfile.objects.get(id=response.json()["id"])
            self.assertEqual(created_profile.firebase_uid, mock_user.uid)

    def test_delete_profile(self):
        profile = MokaProfileFactory()
        with mock.patch(
            "moka_profile.api.v1.FirebaseAuthentication.authenticate",
            return_value=profile,
        ), mock.patch(
            "firebase_admin.auth.delete_user",
            return_value=None,
        ) as firebase_call:
            response = self.client.post(
                path=f"/v1/profile/delete",
                data={},
                content_type="application/json",
            )
            firebase_call.assert_called_with(
                uid=profile.firebase_uid,
            )
            self.assertEqual(response.status_code, 200)

        with self.assertRaises(MokaProfile.DoesNotExist):
            MokaProfile.objects.get(id=profile.id)
