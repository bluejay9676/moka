# Generated by Django 3.2.13 on 2022-06-21 05:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('episode', '0003_delete_page'),
        ('image', '0002_delete_page'),
    ]

    operations = [
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField()),
                ('status', models.CharField(choices=[('PUBLIC', 'Public'), ('DRAFT', 'Draft'), ('REMOVED', 'Removed')], max_length=10)),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.PositiveSmallIntegerField()),
                ('episode', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pages', related_query_name='page', to='episode.episode')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
