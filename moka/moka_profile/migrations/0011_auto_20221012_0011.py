# Generated by Django 3.2.15 on 2022-10-12 00:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('moka_profile', '0010_mokaprofile_is_banned'),
    ]

    operations = [
        migrations.RenameField(
            model_name='follow',
            old_name='profile_id',
            new_name='followee',
        ),
        migrations.RenameField(
            model_name='follow',
            old_name='following_profile_id',
            new_name='follower',
        ),
        migrations.RemoveField(
            model_name='follow',
            name='notify',
        ),
    ]
