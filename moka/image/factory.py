import datetime
from uuid import uuid4

import factory
import factory.fuzzy
from image.models import Image, Page, Storage, Thumbnail
from moka_profile.factory import MokaProfileFactory


class ThumbnailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Thumbnail

    external_id = factory.Sequence(lambda n: uuid4())

    owner = factory.SubFactory(MokaProfileFactory)

    # To override the randomness, add status when calling the factory
    status = factory.fuzzy.FuzzyChoice(
        choices=[
            Image.ImageStatus.DRAFT,
            Image.ImageStatus.PUBLIC,
            Image.ImageStatus.REMOVED,
        ]
    )
    storage = factory.fuzzy.FuzzyChoice(
        choices=[
            Storage.GOOGLE_CLOUD_STORAGE,
        ]
    )

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


class PageFactory(factory.django.DjangoModelFactory):
    """
    Need to provide episode=Episode
    """

    class Meta:
        model = Page

    order = factory.Sequence(lambda n: n)
    external_id = factory.Sequence(lambda n: uuid4())
    owner = factory.SubFactory(MokaProfileFactory)

    # To override the randomness, add status when calling the factory
    status = factory.fuzzy.FuzzyChoice(
        choices=[
            Image.ImageStatus.DRAFT,
            Image.ImageStatus.PUBLIC,
            Image.ImageStatus.REMOVED,
        ]
    )
    storage = factory.fuzzy.FuzzyChoice(
        choices=[
            Storage.GOOGLE_CLOUD_STORAGE,
        ]
    )

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
