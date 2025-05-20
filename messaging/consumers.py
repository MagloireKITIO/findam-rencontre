# messaging/consumers.py

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Conversation, Message, MessageReceipt

User = get_user_model()
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Récupérer l'utilisateur depuis le scope
        self.user = self.scope["user"]
        
        logger.info(f"Tentative de connexion WebSocket par utilisateur {self.user}")
        
        if self.user is None or self.user.is_anonymous:
            # Refuser la connexion si l'utilisateur n'est pas authentifié
            logger.warning("Connexion WebSocket refusée: utilisateur non authentifié")
            await self.close()
            return
        
        # Créer un groupe de chat pour l'utilisateur
        self.user_group_name = f"user_{self.user.id}"
        logger.info(f"Utilisateur {self.user.id} rejoint le groupe {self.user_group_name}")
        
        # Rejoindre le groupe de l'utilisateur
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Accepter la connexion
        await self.accept()
        logger.info(f"Connexion WebSocket acceptée pour l'utilisateur {self.user.id}")
    
    async def disconnect(self, close_code):
        # Quitter le groupe de l'utilisateur
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            logger.info(f"Utilisateur {self.user.id} a quitté le groupe {self.user_group_name}")
        
        logger.info(f"Déconnexion WebSocket pour l'utilisateur {self.user.id if hasattr(self, 'user') else 'inconnu'}, code: {close_code}")
    
    async def receive(self, text_data):
        """Réception d'un message du client WebSocket"""
        try:
            logger.info(f"Message WebSocket reçu: {text_data[:100]}...")
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'send_message':
                # Envoi d'un nouveau message
                conversation_id = data.get('conversation_id')
                content = data.get('content')
                message_type = data.get('message_type', 'TEXT')
                
                logger.info(f"Action 'send_message' pour conversation {conversation_id}")
                
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
                    participants = await self.get_participants(conversation_id)
                    for participant in participants:
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
                                    'is_read': False,
                                    'is_sender': False  # Sera modifié côté client
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
                                    'updated_at': conversation.updated_at.isoformat(),
                                    'last_message': {
                                        'id': message.id,
                                        'content': content,
                                        'sender_id': self.user.id,
                                        'created_at': message.created_at.isoformat()
                                    }
                                }
                            }
                        )
            
            elif action == 'mark_as_read':
                # Marquer un message comme lu
                message_id = data.get('message_id')
                logger.info(f"Action 'mark_as_read' pour message {message_id}")
                
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
                logger.info(f"Action 'join_conversation' pour conversation {conversation_id}")
                
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
                else:
                    logger.warning(f"Utilisateur {self.user.id} a tenté de rejoindre conversation {conversation_id} sans autorisation")
            
            elif action == 'leave_conversation':
                # Quitter une conversation
                conversation_id = data.get('conversation_id')
                logger.info(f"Action 'leave_conversation' pour conversation {conversation_id}")
                
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
                logger.info(f"Action 'typing' pour conversation {conversation_id}")
                
                # Vérifier que l'utilisateur est autorisé à accéder à cette conversation
                if await self.user_in_conversation(self.user.id, conversation_id):
                    # Notifier les autres participants
                    participants = await self.get_participants(conversation_id)
                    for participant in participants:
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
            logger.error(f"Erreur dans receive: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def chat_message(self, event):
        """Envoyer un message au client WebSocket"""
        # Ajuster is_sender pour le destinataire
        message = event['message']
        message['is_sender'] = message['sender_id'] == self.user.id
        
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': message
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
                logger.warning(f"Utilisateur {sender.id} a tenté de créer un message dans conversation {conversation_id} sans autorisation")
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
            
            logger.info(f"Message {message.id} créé dans conversation {conversation_id}")
            return message
        except Conversation.DoesNotExist:
            logger.warning(f"Tentative de création de message dans conversation inexistante {conversation_id}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la création de message: {str(e)}", exc_info=True)
            return None
    
    @database_sync_to_async
    def get_conversation(self, conversation_id):
        """Récupérer une conversation"""
        try:
            return Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            logger.warning(f"Conversation {conversation_id} non trouvée")
            return None
    
    @database_sync_to_async
    def get_participants(self, conversation_id):
        """Récupérer les participants d'une conversation"""
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            return list(conversation.participants.all())
        except Conversation.DoesNotExist:
            logger.warning(f"Conversation {conversation_id} non trouvée lors de la récupération des participants")
            return []
    
    @database_sync_to_async
    def user_in_conversation(self, user_id, conversation_id):
        """Vérifier si un utilisateur fait partie d'une conversation"""
        result = Conversation.objects.filter(
            id=conversation_id, 
            participants__id=user_id
        ).exists()
        
        if not result:
            logger.warning(f"Utilisateur {user_id} a tenté d'accéder à conversation {conversation_id} sans autorisation")
        
        return result
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Marquer un message comme lu"""
        try:
            message = Message.objects.get(id=message_id)
            
            # Ne pas marquer les messages de l'utilisateur actuel
            if message.sender.id != self.user.id:
                message.is_read = True
                message.save(update_fields=['is_read'])
                logger.info(f"Message {message_id} marqué comme lu par utilisateur {self.user.id}")
                
            return message
        except Message.DoesNotExist:
            logger.warning(f"Tentative de marquer comme lu un message inexistant {message_id}")
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
            
            count = 0
            for message in unread_messages:
                # Créer un accusé de réception "livré"
                receipt, created = MessageReceipt.objects.get_or_create(
                    message=message,
                    recipient=self.user,
                    defaults={'status': 'DELIVERED'}
                )
                
                if created or receipt.status != 'DELIVERED':
                    count += 1
                    if not created:
                        receipt.status = 'DELIVERED'
                        receipt.save(update_fields=['status', 'timestamp'])
            
            if count > 0:
                logger.info(f"{count} messages marqués comme livrés dans conversation {conversation_id}")
            
            return True
        except Conversation.DoesNotExist:
            logger.warning(f"Tentative de marquer messages comme livrés dans conversation inexistante {conversation_id}")
            return False
    
    @database_sync_to_async
    def create_message_receipt(self, message, recipient, status):
        """Créer ou mettre à jour un accusé de réception"""
        try:
            receipt, created = MessageReceipt.objects.get_or_create(
                message=message,
                recipient=recipient,
                defaults={'status': status}
            )
            
            if not created and receipt.status != status:
                receipt.status = status
                receipt.save(update_fields=['status', 'timestamp'])
                logger.info(f"Accusé réception mis à jour pour message {message.id}, destinataire {recipient.id}, status {status}")
            elif created:
                logger.info(f"Accusé réception créé pour message {message.id}, destinataire {recipient.id}, status {status}")
            
            return receipt
        except Exception as e:
            logger.error(f"Erreur lors de la création d'accusé réception: {str(e)}", exc_info=True)
            return None