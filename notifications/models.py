# notifications/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL

class Notification(models.Model):
    """Modèle pour les notifications des utilisateurs"""
    
    TYPE_CHOICES = (
        ('MATCH', 'Nouveau match'),
        ('MESSAGE', 'Nouveau message'),
        ('LIKE', 'Nouveau like'),
        ('EVENT', 'Événement'),
        ('SUBSCRIPTION', 'Abonnement'),
        ('SYSTEM', 'Système'),
    )
    
    CONTEXT_CHOICES = (
        ('USER', 'Utilisateur'),
        ('EVENT', 'Événement'),
        ('MESSAGE', 'Message'),
        ('SUBSCRIPTION', 'Abonnement'),
        ('SYSTEM', 'Système'),
    )
    
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        verbose_name=_("Destinataire")
    )
    notification_type = models.CharField(
        max_length=15,
        choices=TYPE_CHOICES,
        verbose_name=_("Type")
    )
    context_type = models.CharField(
        max_length=15,
        choices=CONTEXT_CHOICES,
        verbose_name=_("Type de contexte")
    )
    context_id = models.PositiveIntegerField(
        verbose_name=_("ID de contexte")
    )
    actor_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("ID de l'acteur")
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_("Titre")
    )
    message = models.TextField(
        verbose_name=_("Message")
    )
    image_url = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("URL de l'image")
    )
    action_url = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("URL d'action")
    )
    action_text = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Texte de l'action")
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_("Lu")
    )
    is_email_sent = models.BooleanField(
        default=False,
        verbose_name=_("Email envoyé")
    )
    is_push_sent = models.BooleanField(
        default=False,
        verbose_name=_("Notification push envoyée")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Créé le")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Mis à jour le")
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
    
    def __str__(self):
        return f"{self.get_notification_type_display()} pour {self.recipient.username}"

class NotificationPreference(models.Model):
    """Préférences de notification des utilisateurs"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_preferences',
        verbose_name=_("Utilisateur")
    )
    receive_email = models.BooleanField(
        default=True,
        verbose_name=_("Recevoir des emails")
    )
    receive_push = models.BooleanField(
        default=True,
        verbose_name=_("Recevoir des notifications push")
    )
    matches = models.BooleanField(
        default=True,
        verbose_name=_("Nouveaux matchs")
    )
    messages = models.BooleanField(
        default=True,
        verbose_name=_("Nouveaux messages")
    )
    likes = models.BooleanField(
        default=True,
        verbose_name=_("Nouveaux likes")
    )
    events = models.BooleanField(
        default=True,
        verbose_name=_("Événements")
    )
    subscription = models.BooleanField(
        default=True,
        verbose_name=_("Abonnement")
    )
    system = models.BooleanField(
        default=True,
        verbose_name=_("Système")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Créé le")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Mis à jour le")
    )
    
    class Meta:
        verbose_name = _("Préférence de notification")
        verbose_name_plural = _("Préférences de notification")
    
    def __str__(self):
        return f"Préférences de notification de {self.user.username}"

class DeviceToken(models.Model):
    """Tokens des appareils pour les notifications push"""
    
    PLATFORM_CHOICES = (
        ('ANDROID', 'Android'),
        ('IOS', 'iOS'),
        ('WEB', 'Web'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='device_tokens',
        verbose_name=_("Utilisateur")
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("Token de l'appareil")
    )
    platform = models.CharField(
        max_length=10,
        choices=PLATFORM_CHOICES,
        verbose_name=_("Plateforme")
    )
    device_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Nom de l'appareil")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Actif")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Créé le")
    )
    last_used = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Dernière utilisation")
    )
    
    class Meta:
        verbose_name = _("Token d'appareil")
        verbose_name_plural = _("Tokens d'appareils")
        unique_together = ('user', 'token')
    
    def __str__(self):
        return f"Appareil {self.device_name} de {self.user.username}"