# Generated by Django 3.2.14 on 2022-07-10 02:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('series', '0003_auto_20220611_1355'),
    ]

    operations = [
        migrations.AlterField(
            model_name='series',
            name='description',
            field=models.CharField(max_length=500, null=True),
        ),
    ]
