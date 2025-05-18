# messaging/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Conversation, Message, MessageReceipt

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Récupérer l'utilisateur depuis le scope
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            # Refuser la connexion si l'utilisateur n'est pas authentifié
            await self.close()
            return
        
        # Créer un groupe de chat pour l'utilisateur
        self.user_group_name = f"user_{self.user.id}"
        
        # Rejoindre le groupe de l'utilisateur
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Accepter la connexion
        await self.accept()
    
    async def disconnect(self, close_code):
        # Quitter le groupe de l'utilisateur
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Réception d'un message du client WebSocket"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'send_message':
                # Envoi d'un nouveau message
                conversation_id = data.get('conversation_id')
                content = data.get('content')
                message_type = data.get('message_type', 'TEXT')
                
                # Créer le message en base de données
                message = await self.create_message(
                    conversation_id=conversation_id,
                    sender=self.user,
                    content=content,
                    message_type=message_type
                )
                
                if message:
                    # Récupérer les détails de la conversation
                    conversation = await self.get_conversation(conversation_id)
                    
                    # Notifier tous les participants de la conversation
                    for participant in await self.get_participants(conversation_id):
                        participant_group = f"user_{participant.id}"
                        
                        # Créer un accusé de réception "envoyé" pour chaque destinataire
                        if participant.id != self.user.id:
                            await self.create_message_receipt(
                                message=message,
                                recipient=participant,
                                status='SENT'
                            )
                        
                        # Envoyer le message à chaque participant
                        await self.channel_layer.group_send(
                            participant_group,
                            {
                                'type': 'chat_message',
                                'message': {
                                    'id': message.id,
                                    'conversation_id': conversation_id,
                                    'sender_id': self.user.id,
                                    'sender_username': self.user.username,
                                    'content': content,
                                    'message_type': message_type,
                                    'created_at': message.created_at.isoformat(),
                                    'is_read': False
                                }
                            }
                        )
                        
                        # Mettre à jour la conversation
                        await self.channel_layer.group_send(
                            participant_group,
                            {
                                'type': 'conversation_update',
                                'conversation': {
                                    'id': conversation.id,
                                    'updated_at': conversation.updated_at.isoformat()
                                }
                            }
                        )
            
            elif action == 'mark_as_read':
                # Marquer un message comme lu
                message_id = data.get('message_id')
                
                # Mettre à jour le message en base de données
                message = await self.mark_message_as_read(message_id)
                
                if message:
                    # Créer un accusé de réception "lu"
                    await self.create_message_receipt(
                        message=message,
                        recipient=self.user,
                        status='READ'
                    )
                    
                    # Notifier l'expéditeur que le message a été lu
                    sender_group = f"user_{message.sender.id}"
                    await self.channel_layer.group_send(
                        sender_group,
                        {
                            'type': 'message_read',
                            'message_id': message_id,
                            'conversation_id': message.conversation.id,
                            'reader_id': self.user.id
                        }
                    )
            
            elif action == 'join_conversation':
                # Rejoindre une conversation spécifique
                conversation_id = data.get('conversation_id')
                
                # Vérifier que l'utilisateur est autorisé à accéder à cette conversation
                if await self.user_in_conversation(self.user.id, conversation_id):
                    self.conversation_group_name = f"conversation_{conversation_id}"
                    await self.channel_layer.group_add(
                        self.conversation_group_name,
                        self.channel_name
                    )
                    
                    # Marquer les messages non lus comme "livrés"
                    await self.mark_messages_as_delivered(conversation_id)
                    
                    # Confirmer l'adhésion à la conversation
                    await self.send(text_data=json.dumps({
                        'type': 'conversation_joined',
                        'conversation_id': conversation_id
                    }))
            
            elif action == 'leave_conversation':
                # Quitter une conversation
                conversation_id = data.get('conversation_id')
                self.conversation_group_name = f"conversation_{conversation_id}"
                await self.channel_layer.group_discard(
                    self.conversation_group_name,
                    self.channel_name
                )
                
                # Confirmer le départ de la conversation
                await self.send(text_data=json.dumps({
                    'type': 'conversation_left',
                    'conversation_id': conversation_id
                }))
                
            elif action == 'typing':
                # Notification de frappe
                conversation_id = data.get('conversation_id')
                
                # Vérifier que l'utilisateur est autorisé à accéder à cette conversation
                if await self.user_in_conversation(self.user.id, conversation_id):
                    # Notifier les autres participants
                    for participant in await self.get_participants(conversation_id):
                        if participant.id != self.user.id:
                            participant_group = f"user_{participant.id}"
                            await self.channel_layer.group_send(
                                participant_group,
                                {
                                    'type': 'user_typing',
                                    'user_id': self.user.id,
                                    'conversation_id': conversation_id
                                }
                            )
        
        except Exception as e:
            # Envoyer une erreur au client
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def chat_message(self, event):
        """Envoyer un message au client WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))
    
    async def message_read(self, event):
        """Notifier que le message a été lu"""
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'conversation_id': event['conversation_id'],
            'reader_id': event['reader_id']
        }))
    
    async def conversation_update(self, event):
        """Notifier d'une mise à jour de conversation"""
        await self.send(text_data=json.dumps({
            'type': 'conversation_update',
            'conversation': event['conversation']
        }))
    
    async def user_typing(self, event):
        """Notifier qu'un utilisateur est en train d'écrire"""
        await self.send(text_data=json.dumps({
            'type': 'user_typing',
            'user_id': event['user_id'],
            'conversation_id': event['conversation_id']
        }))
    
    @database_sync_to_async
    def create_message(self, conversation_id, sender, content, message_type):
        """Créer un nouveau message en base de données"""
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Vérifier que l'utilisateur est un participant de la conversation
            if not conversation.participants.filter(id=sender.id).exists():
                return None
            
            # Créer le message
            message = Message.objects.create(
                conversation=conversation,
                sender=sender,
                content=content,
                message_type=message_type
            )
            
            # Mettre à jour la date de dernière activité de la conversation
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=['updated_at'])
            
            return message
        except Conversation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_conversation(self, conversation_id):
        """Récupérer une conversation"""
        try:
            return Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_participants(self, conversation_id):
        """Récupérer les participants d'une conversation"""
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            return list(conversation.participants.all())
        except Conversation.DoesNotExist:
            return []
    
    @database_sync_to_async
    def user_in_conversation(self, user_id, conversation_id):
        """Vérifier si un utilisateur fait partie d'une conversation"""
        return Conversation.objects.filter(
            id=conversation_id, 
            participants__id=user_id
        ).exists()
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Marquer un message comme lu"""
        try:
            message = Message.objects.get(id=message_id)
            
            # Ne pas marquer les messages de l'utilisateur actuel
            if message.sender.id != self.user.id:
                message.is_read = True
                message.save(update_fields=['is_read'])
                
            return message
        except Message.DoesNotExist:
            return None
    
    @database_sync_to_async
    def mark_messages_as_delivered(self, conversation_id):
        """Marquer les messages non lus d'une conversation comme livrés"""
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Récupérer les messages non lus envoyés par d'autres utilisateurs
            unread_messages = Message.objects.filter(
                conversation=conversation,
                is_read=False
            ).exclude(sender=self.user)
            
            for message in unread_messages:
                # Créer un accusé de réception "livré"
                MessageReceipt.objects.get_or_create(
                    message=message,
                    recipient=self.user,
                    defaults={'status': 'DELIVERED'}
                )
            
            return True
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message_receipt(self, message, recipient, status):
        """Créer ou mettre à jour un accusé de réception"""
        receipt, created = MessageReceipt.objects.get_or_create(
            message=message,
            recipient=recipient,
            defaults={'status': status}
        )
        
        if not created and receipt.status != status:
            receipt.status = status
            receipt.save(update_fields=['status'])
            
        return receipt