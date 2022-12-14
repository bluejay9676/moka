# Generated by Django 3.2.14 on 2022-08-10 04:36
# import datetime

from django.db import migrations
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps

# from moka_profile.models import MokaProfile


def early_adopter_high_value_status(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    """
    Set the payout status for the users before this as High value
    """
    # This can cause failure in creating test database by trying to fetch MokaProfile with is_banned field.
    # Uncomment this if you need to run this script again
    # profile_made_before_cutoff = MokaProfile.objects.filter(
    #     created_at__lte=datetime.datetime(year=2022, month=8, day=15).replace(tzinfo=datetime.timezone.utc)
    # )
    # for profile in profile_made_before_cutoff:
    #     profile.payout_status = MokaProfile.PayoutStatus.HIGH_VALUE

    # MokaProfile.objects.bulk_update(profile_made_before_cutoff, fields=['payout_status'])
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('moka_profile', '0007_mokaprofile_payout_status'),
    ]

    operations = [
        migrations.RunPython(early_adopter_high_value_status)
    ]
