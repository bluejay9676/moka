# Generated by Django 3.2.14 on 2022-08-10 18:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moka_profile', '0007_mokaprofile_payout_status'),
        ('episode', '0007_auto_20220806_2203'),
    ]

    operations = [
        migrations.RenameField(
            model_name='episode',
            old_name='premium',
            new_name='is_premium',
        ),
        migrations.AddField(
            model_name='episode',
            name='price',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='PurchaseEpisode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('episode', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='episode.episode')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='moka_profile.mokaprofile')),
            ],
        ),
    ]
