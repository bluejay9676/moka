# Generated by Django 3.2.14 on 2022-08-07 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moka_profile', '0004_mokaprofile_display_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mokaprofile',
            name='display_name',
            field=models.CharField(max_length=200, null=True, unique=True),
        ),
    ]
