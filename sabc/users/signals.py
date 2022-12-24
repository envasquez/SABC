# -*- coding: utf-8 -*-
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User

from .models import Angler


@receiver(post_save, sender=User)
def create_angler(sender, instance, created, **kwargs):
    if created:
        Angler.objects.update_or_create(user=instance)


@receiver(post_save, sender=User)
def save_angler(sender, instance, **kwargs):
    instance.angler.save()
