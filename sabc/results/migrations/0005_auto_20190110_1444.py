# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-01-10 14:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0004_tournamentresult_day_num'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournamentresult',
            name='tournament',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tournaments.Tournament'),
        ),
    ]
