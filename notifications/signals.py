# notifications/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import Notification, NotificationPreference

User = get_user_model()

@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """Crée automatiquement des préférences de notification lors de la création d'un utilisateur"""
    if created:
        NotificationPreference.objects.create(user=instance)

@receiver(post_save, sender=Notification)
def send_notification_to_websocket(sender, instance, created, **kwargs):
    """Envoie une notification via WebSocket lorsqu'une nouvelle notification est créée"""
    if created:
        channel_layer = get_channel_layer()
        
        if channel_layer:
            # Préparer les données de la notification
            notification_data = {
                'id': instance.id,
                'notification_type': instance.notification_type,
                'context_type': instance.context_type,
                'context_id': instance.context_id,
                'actor_id': instance.actor_id,
                'title': instance.title,
                'message': instance.message,
                'image_url': instance.image_url,
                'action_url': instance.action_url,
                'action_text': instance.action_text,
                'created_at': instance.created_at.isoformat()
            }
            
            # Envoyer la notification au groupe de l'utilisateur
            try:
                async_to_sync(channel_layer.group_send)(
                    f"notifications_{instance.recipient.id}",
                    {
                        'type': 'notification',
                        'notification': notification_data
                    }
                )
            except Exception:
                pass