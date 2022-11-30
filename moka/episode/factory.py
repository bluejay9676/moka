import datetime

import factory
import factory.fuzzy
from episode.models import Episode
from image.factory import ThumbnailFactory
from series.factory import SeriesFactory


class EpisodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Episode

    series = factory.SubFactory(SeriesFactory)
    thumbnail = factory.SubFactory(ThumbnailFactory)
    title = factory.Faker("word")
    status = factory.fuzzy.FuzzyChoice(
        choices=[
            Episode.EpisodeStatus.PUBLIC,
            Episode.EpisodeStatus.DRAFT,
        ]
    )

    episode_number = factory.Sequence(lambda n: n)

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

    views = 10

    @factory.post_generation
    def likes(self, create, extracted, **kwargs):
        if not create or not extracted:
            # Simple build, or nothing to add, do nothing.
            return

        # Add the iterable of groups using bulk addition
        self.likes.add(*extracted)
