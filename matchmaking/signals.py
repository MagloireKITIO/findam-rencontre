# matchmaking/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import UserPreference, Match

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    """Crée automatiquement des préférences utilisateur lors de la création d'un utilisateur"""
    if created:
        UserPreference.objects.create(user=instance)

@receiver(post_save, sender=Match)
def notify_match(sender, instance, created, **kwargs):
    """Notifie les utilisateurs d'un nouveau match"""
    if created:
        # La notification sera implémentée dans l'application notifications
        # Ce signal sera utilisé pour déclencher la création de notifications
        pass