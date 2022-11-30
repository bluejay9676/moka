import datetime

import factory
import factory.fuzzy
from moka_profile.models import MokaProfile


class MokaProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MokaProfile

    display_name = factory.Sequence(lambda n: f"Moka_User_{n}")
    firebase_uid = factory.Sequence(lambda n: f"test_moka_profile_{n}")
    description = factory.Faker("sentence")

    created_at = factory.fuzzy.FuzzyDateTime(
        datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        - datetime.timedelta(days=10),
        datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        - datetime.timedelta(days=1),
    )
    updated_at = factory.fuzzy.FuzzyDateTime(
        datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        - datetime.timedelta(days=10),
        datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        - datetime.timedelta(days=1),
    )
