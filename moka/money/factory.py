import factory
import factory.fuzzy
from moka_profile.factory import MokaProfileFactory
from money.models import Wallet


class WalletFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Wallet

    owner = factory.SubFactory(MokaProfileFactory)
