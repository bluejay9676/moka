# Generated by Django 3.2.15 on 2022-10-12 05:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moka_profile', '0011_auto_20221012_0011'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='follow',
            name='unique_followers',
        ),
        migrations.AlterField(
            model_name='follow',
            name='followee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='followers', to='moka_profile.mokaprofile'),
        ),
        migrations.AlterField(
            model_name='follow',
            name='follower',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='following', to='moka_profile.mokaprofile'),
        ),
        migrations.AddConstraint(
            model_name='follow',
            constraint=models.UniqueConstraint(fields=('followee', 'follower'), name='unique_followers'),
        ),
    ]
