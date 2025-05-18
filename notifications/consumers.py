# notifications/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from .models import Notification

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Récupérer l'utilisateur depuis le scope
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            # Refuser la connexion si l'utilisateur n'est pas authentifié
            await self.close()
            return
        
        # Créer un groupe de notification pour l'utilisateur
        self.notification_group_name = f"notifications_{self.user.id}"
        
        # Rejoindre le groupe
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        # Accepter la connexion
        await self.accept()
        
        # Envoyer les notifications non lues
        unread_notifications = await self.get_unread_notifications()
        if unread_notifications:
            await self.send(text_data=json.dumps({
                'type': 'unread_notifications',
                'notifications': unread_notifications,
                'count': len(unread_notifications)
            }))
    
    async def disconnect(self, close_code):
        # Quitter le groupe
        await self.channel_layer.group_discard(
            self.notification_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Réception d'un message du client WebSocket"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_as_read':
                # Marquer une notification comme lue
                notification_id = data.get('notification_id')
                if notification_id:
                    marked = await self.mark_notification_as_read(notification_id)
                    if marked:
                        await self.send(text_data=json.dumps({
                            'type': 'notification_marked_as_read',
                            'notification_id': notification_id
                        }))
            
            elif action == 'mark_all_as_read':
                # Marquer toutes les notifications comme lues
                count = await self.mark_all_notifications_as_read()
                await self.send(text_data=json.dumps({
                    'type': 'all_notifications_marked_as_read',
                    'count': count
                }))
        
        except Exception as e:
            # Envoyer une erreur au client
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def notification(self, event):
        """Envoyer une notification au client WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """Récupérer les notifications non lues de l'utilisateur"""
        notifications = Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).order_by('-created_at')[:20]
        
        return [
            {
                'id': notification.id,
                'notification_type': notification.notification_type,
                'context_type': notification.context_type,
                'context_id': notification.context_id,
                'actor_id': notification.actor_id,
                'title': notification.title,
                'message': notification.message,
                'image_url': notification.image_url,
                'action_url': notification.action_url,
                'action_text': notification.action_text,
                'created_at': notification.created_at.isoformat()
            }
            for notification in notifications
        ]
    
    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """Marquer une notification comme lue"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_notifications_as_read(self):
        """Marquer toutes les notifications de l'utilisateur comme lues"""
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).update(is_read=True)