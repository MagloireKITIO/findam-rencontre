# accounts/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import UserProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Crée automatiquement un profil utilisateur lors de la création d'un utilisateur"""
    if created:
        # Vérifier si un profil existe déjà avant d'en créer un nouveau
        if not hasattr(instance, 'profile'):
            UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """S'assure que le profil utilisateur est sauvegardé en même temps que l'utilisateur"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
   