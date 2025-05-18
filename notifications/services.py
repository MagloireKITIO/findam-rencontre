# notifications/services.py

from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import send_mail

from .models import Notification, NotificationPreference, DeviceToken

User = get_user_model()

class NotificationService:
    """
    Service pour envoyer différents types de notifications
    """
    
    @staticmethod
    def send_notification(
        recipient_id, 
        notification_type, 
        context_type, 
        context_id,
        actor_id=None,
        title="",
        message="",
        image_url=None,
        action_url=None,
        action_text=None,
        send_email=True,
        send_push=True
    ):
        """
        Envoie une notification à un utilisateur
        
        Args:
            recipient_id: ID de l'utilisateur destinataire
            notification_type: Type de notification (MATCH, MESSAGE, etc.)
            context_type: Type de contexte (USER, EVENT, etc.)
            context_id: ID du contexte
            actor_id: ID de l'utilisateur acteur (optionnel)
            title: Titre de la notification
            message: Message de la notification
            image_url: URL de l'image (optionnel)
            action_url: URL d'action (optionnel)
            action_text: Texte de l'action (optionnel)
            send_email: Envoyer un email (par défaut: True)
            send_push: Envoyer une notification push (par défaut: True)
            
        Returns:
            Notification: L'objet notification créé
        """
        try:
            # Vérifier si l'utilisateur existe
            recipient = User.objects.get(id=recipient_id)
            
            # Vérifier les préférences de notification de l'utilisateur
            preferences, created = NotificationPreference.objects.get_or_create(user=recipient)
            
            # Vérifier si l'utilisateur souhaite recevoir ce type de notification
            should_send = getattr(preferences, notification_type.lower(), True)
            
            if not should_send:
                return None
            
            # Créer la notification
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                context_type=context_type,
                context_id=context_id,
                actor_id=actor_id,
                title=title,
                message=message,
                image_url=image_url,
                action_url=action_url,
                action_text=action_text
            )
            
            # Envoyer par email si nécessaire
            if send_email and preferences.receive_email:
                NotificationService.send_email_notification(notification)
            
            # Envoyer par push si nécessaire
            if send_push and preferences.receive_push:
                NotificationService.send_push_notification(notification)
            
            return notification
        
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def send_email_notification(notification):
        """
        Envoie une notification par email
        
        Args:
            notification: L'objet notification
            
        Returns:
            bool: True si l'email a été envoyé, False sinon
        """
        recipient = notification.recipient
        
        try:
            # Préparer le contenu de l'email
            context = {
                'notification': notification,
                'user': recipient,
                'site_name': settings.SITE_NAME,
                'site_url': settings.SITE_URL,
            }
            
            subject = notification.title
            
            html_content = render_to_string('notifications/email_notification.html', context)
            text_content = render_to_string('notifications/email_notification.txt', context)
            
            # Envoyer l'email
            sent = send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                html_message=html_content,
                fail_silently=False
            )
            
            # Mettre à jour la notification
            if sent:
                notification.is_email_sent = True
                notification.save(update_fields=['is_email_sent'])
                return True
            
            return False
        
        except Exception:
            return False
    
    @staticmethod
    def send_push_notification(notification):
        """
        Envoie une notification push
        
        Args:
            notification: L'objet notification
            
        Returns:
            bool: True si la notification push a été envoyée, False sinon
        """
        recipient = notification.recipient
        
        try:
            # Récupérer les tokens actifs de l'utilisateur
            device_tokens = DeviceToken.objects.filter(
                user=recipient,
                is_active=True
            )
            
            if not device_tokens.exists():
                return False
            
            # Préparer les données de la notification
            notification_data = {
                'title': notification.title,
                'body': notification.message,
                'icon': settings.SITE_ICON_URL,
                'click_action': notification.action_url or settings.SITE_URL,
                'data': {
                    'notification_id': notification.id,
                    'notification_type': notification.notification_type,
                    'context_type': notification.context_type,
                    'context_id': notification.context_id,
                    'action_url': notification.action_url,
                }
            }
            
            # Ici, vous pouvez utiliser un service de notification push comme Firebase
            # Pour simplifier, on simule l'envoi
            sent = True
            
            # Mettre à jour la notification
            if sent:
                notification.is_push_sent = True
                notification.save(update_fields=['is_push_sent'])
                return True
            
            return False
        
        except Exception:
            return False
    
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """
        Marque une notification comme lue
        
        Args:
            notification_id: ID de la notification
            user_id: ID de l'utilisateur
            
        Returns:
            bool: True si la notification a été marquée comme lue, False sinon
        """
        try:
            notification = Notification.objects.get(id=notification_id, recipient_id=user_id)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def mark_all_as_read(user_id):
        """
        Marque toutes les notifications d'un utilisateur comme lues
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            int: Nombre de notifications marquées comme lues
        """
        return Notification.objects.filter(
            recipient_id=user_id,
            is_read=False
        ).update(is_read=True)
    
    @staticmethod
    def register_device(user_id, token, platform, device_name=None):
        """
        Enregistre un appareil pour les notifications push
        
        Args:
            user_id: ID de l'utilisateur
            token: Token de l'appareil
            platform: Plateforme (ANDROID, IOS, WEB)
            device_name: Nom de l'appareil (optionnel)
            
        Returns:
            DeviceToken: L'objet token créé ou mis à jour
        """
        try:
            user = User.objects.get(id=user_id)
            
            # Vérifier si le token existe déjà
            device_token, created = DeviceToken.objects.get_or_create(
                token=token,
                defaults={
                    'user': user,
                    'platform': platform,
                    'device_name': device_name,
                    'is_active': True
                }
            )
            
            if not created:
                # Mettre à jour l'utilisateur si le token existe déjà
                device_token.user = user
                device_token.platform = platform
                if device_name:
                    device_token.device_name = device_name
                device_token.is_active = True
                device_token.save()
            
            return device_token
        
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def unregister_device(token):
        """
        Désactive un appareil pour les notifications push
        
        Args:
            token: Token de l'appareil
            
        Returns:
            bool: True si l'appareil a été désactivé, False sinon
        """
        try:
            device_token = DeviceToken.objects.get(token=token)
            device_token.is_active = False
            device_token.save(update_fields=['is_active'])
            return True
        except DeviceToken.DoesNotExist:
            return False