# Generated by Django 3.2.15 on 2022-09-29 17:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('moka_profile', '0010_mokaprofile_is_banned'),
        ('episode', '0010_episode_is_nsfw'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('commenter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', related_query_name='comment', to='moka_profile.mokaprofile')),
                ('episode', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', related_query_name='comment', to='episode.episode')),
                ('parent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='comment.comment')),
            ],
        ),
        migrations.CreateModel(
            name='LikeComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', related_query_name='like', to='comment.comment')),
                ('liker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='liked_comments', related_query_name='liked_comment', to='moka_profile.mokaprofile')),
            ],
        ),
        migrations.AddConstraint(
            model_name='likecomment',
            constraint=models.UniqueConstraint(fields=('comment', 'liker'), name='unique_comment_liker'),
        ),
    ]
