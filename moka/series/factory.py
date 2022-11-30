import datetime

import factory
import factory.fuzzy
from image.factory import ThumbnailFactory
from moka_profile.factory import MokaProfileFactory
from series.models import Series


class SeriesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Series

    owner = factory.SubFactory(MokaProfileFactory)
    thumbnail = factory.SubFactory(ThumbnailFactory)

    title = factory.Faker("word")
    description = factory.Faker("sentence")
    status = factory.fuzzy.FuzzyChoice(
        choices=[
            Series.SeriesStatus.PUBLIC,
            Series.SeriesStatus.DRAFT,
        ]
    )

    publish_date = factory.fuzzy.FuzzyDateTime(
        datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        - datetime.timedelta(days=10),
        datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        - datetime.timedelta(days=1),
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

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of tags were passed in, use them.
            for tag in extracted:
                self.tags.add(tag)
