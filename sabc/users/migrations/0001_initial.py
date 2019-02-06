# -*- coding: utf-8 -*-
# pylint: disable=all
# Generated by Django 1.11 on 2019-01-10 00:50
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True,
                                        primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[
                 ('guest', 'guest'), ('member', 'member'), ('officer', 'officer')], max_length=10)),
                ('date_joined', models.DateTimeField(
                    default=django.utils.timezone.now)),
                ('phone_number', models.CharField(max_length=15)),
                ('organization', models.CharField(blank=True, choices=[
                 ('SABC', 'South Austin Bass Club')], default='SABC', max_length=100, null=True)),
                ('deleted', models.BooleanField(default=False)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Profiles',
            },
        ),
    ]
