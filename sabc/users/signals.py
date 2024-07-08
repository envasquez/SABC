# -*- coding: utf-8 -*-

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Angler

User = get_user_model()


@receiver(post_save, sender=User)
def create_angler(sender, instance, created, **kwargs):
    del sender, kwargs
    if created:
        Angler.objects.update_or_create(user=instance)


@receiver(post_save, sender=User)
def save_angler(sender, instance, **kwargs):
    del sender, kwargs
    instance.angler.save()
