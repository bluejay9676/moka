# Generated by Django 3.2.15 on 2022-08-24 22:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('episode', '0008_auto_20220810_1820'),
    ]

    operations = [
        migrations.AddField(
            model_name='episode',
            name='is_banned',
            field=models.BooleanField(default=False),
        ),
    ]
