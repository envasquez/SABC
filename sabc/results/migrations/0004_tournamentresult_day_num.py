# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-01-10 14:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0003_tournamentresult_tournament'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournamentresult',
            name='day_num',
            field=models.IntegerField(default=1),
        ),
    ]
