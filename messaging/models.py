# messaging/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL

class Conversation(models.Model):
    """Modèle pour les conversations entre utilisateurs"""
    
    participants = models.ManyToManyField(
        User, 
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation {self.id}"
    
    def get_other_participant(self, user):
        """Récupère l'autre participant de la conversation"""
        return self.participants.exclude(id=user.id).first()

class Message(models.Model):
    """Modèle pour les messages dans une conversation"""
    
    TYPE_CHOICES = (
        ('TEXT', 'Texte'),
        ('IMAGE', 'Image'),
        ('AUDIO', 'Audio'),
        ('VIDEO', 'Vidéo'),
        ('LOCATION', 'Localisation'),
    )
    
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    content = models.TextField()
    message_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='TEXT'
    )
    attachment = models.FileField(
        upload_to='message_attachments',
        null=True,
        blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message {self.id} de {self.sender.username}"

class MessageReceipt(models.Model):
    """Modèle pour les accusés de réception des messages"""
    
    RECEIPT_CHOICES = (
        ('SENT', 'Envoyé'),
        ('DELIVERED', 'Livré'),
        ('READ', 'Lu'),
    )
    
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='receipts'
    )
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='message_receipts'
    )
    status = models.CharField(
        max_length=10,
        choices=RECEIPT_CHOICES,
        default='SENT'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'recipient')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_status_display()} à {self.recipient.username}"

class DeletedMessage(models.Model):
    """Modèle pour les messages supprimés par un utilisateur"""
    
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='deleted_by'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='deleted_messages'
    )
    deleted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
    
    def __str__(self):
        return f"Message {self.message.id} supprimé par {self.user.username}"