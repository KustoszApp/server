from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from readorganizer_api import models


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        profile = models.Profile(user=instance)
        profile.save()
