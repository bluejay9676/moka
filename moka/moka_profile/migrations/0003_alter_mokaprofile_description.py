# Generated by Django 3.2.14 on 2022-07-10 02:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moka_profile', '0002_mokaprofile_thumbnail'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mokaprofile',
            name='description',
            field=models.CharField(max_length=500, null=True),
        ),
    ]