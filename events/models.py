# events/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL

class EventCategory(models.Model):
    """Catégories d'événements"""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Nom de l'icône")
    
    class Meta:
        verbose_name = "Catégorie d'événement"
        verbose_name_plural = "Catégories d'événements"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Event(models.Model):
    """Événements locaux"""
    
    STATUS_CHOICES = (
        ('DRAFT', 'Brouillon'),
        ('PUBLISHED', 'Publié'),
        ('CANCELLED', 'Annulé'),
        ('COMPLETED', 'Terminé'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        EventCategory, 
        on_delete=models.SET_NULL,
        related_name='events',
        null=True,
        blank=True
    )
    image = models.ImageField(upload_to='event_images', blank=True)
    location_name = models.CharField(max_length=200)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Prix en FCFA")
    is_free = models.BooleanField(default=False)
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    registration_required = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return self.title

class EventParticipant(models.Model):
    """Participants aux événements"""
    
    STATUS_CHOICES = (
        ('REGISTERED', 'Inscrit'),
        ('CONFIRMED', 'Confirmé'),
        ('ATTENDED', 'Présent'),
        ('CANCELLED', 'Annulé'),
    )
    
    event = models.ForeignKey(
        Event, 
        on_delete=models.CASCADE, 
        related_name='participants'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='event_participations'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='REGISTERED'
    )
    registration_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('event', 'user')
        ordering = ['registration_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.event.title}"

class EventComment(models.Model):
    """Commentaires sur les événements"""
    
    event = models.ForeignKey(
        Event, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='event_comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Commentaire de {self.user.username} sur {self.event.title}"

class EventSavedByUser(models.Model):
    """Événements sauvegardés par les utilisateurs"""
    
    event = models.ForeignKey(
        Event, 
        on_delete=models.CASCADE, 
        related_name='saved_by'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='saved_events'
    )
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-saved_at']
    
    def __str__(self):
        return f"{self.event.title} sauvegardé par {self.user.username}"