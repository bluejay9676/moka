# Generated by Django 3.2.14 on 2022-07-27 02:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moka_profile', '0003_alter_mokaprofile_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='mokaprofile',
            name='display_name',
            field=models.CharField(max_length=200, null=True),
        ),
    ]
