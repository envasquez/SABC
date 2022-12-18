from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User

from .models import Angler


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Creates an Angler everytime a User is created"""
    if created:
        Angler.objects.update_or_create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    """Save an angler's profile"""
    instance.angler.save()
