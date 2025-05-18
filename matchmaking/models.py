# matchmaking/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL

class Like(models.Model):
    """Modèle pour les likes entre utilisateurs"""
    
    liker = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='likes_given'
    )
    liked = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='likes_received'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('liker', 'liked')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.liker.username} → {self.liked.username}"

class Dislike(models.Model):
    """Modèle pour les dislikes entre utilisateurs"""
    
    disliker = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='dislikes_given'
    )
    disliked = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='dislikes_received'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('disliker', 'disliked')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.disliker.username} ✗ {self.disliked.username}"

class Match(models.Model):
    """Modèle pour les matchs entre utilisateurs"""
    
    user1 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='matches_as_user1'
    )
    user2 = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='matches_as_user2'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('user1', 'user2')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Match entre {self.user1.username} et {self.user2.username}"

class BlockedUser(models.Model):
    """Modèle pour les utilisateurs bloqués"""
    
    blocker = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='blocked_users'
    )
    blocked = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='blocked_by'
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.blocker.username} a bloqué {self.blocked.username}"

class SwipeAction(models.Model):
    """Modèle pour suivre toutes les actions de swipe"""
    
    ACTION_CHOICES = (
        ('L', 'Like'),
        ('D', 'Dislike'),
        ('S', 'SuperLike'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='swipe_actions'
    )
    target = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='targeted_by'
    )
    action = models.CharField(max_length=1, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} a fait {self.get_action_display()} sur {self.target.username}"

class UserPreference(models.Model):
    """Préférences de recherche des utilisateurs"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='preferences'
    )
    min_age = models.PositiveSmallIntegerField(default=18)
    max_age = models.PositiveSmallIntegerField(default=50)
    distance = models.PositiveSmallIntegerField(
        default=50,
        help_text="Distance maximale en kilomètres"
    )
    show_verified_only = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Préférences de {self.user.username}"

class Report(models.Model):
    """Signalements d'utilisateurs"""
    
    REASON_CHOICES = (
        ('FAKE', 'Profil fake'),
        ('INAP', 'Contenu inapproprié'),
        ('SPAM', 'Spam'),
        ('HARR', 'Harcèlement'),
        ('HATE', 'Discours haineux'),
        ('OTHR', 'Autre'),
    )
    
    reporter = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reports_submitted'
    )
    reported = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reports_received'
    )
    reason = models.CharField(max_length=4, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    is_reviewed = models.BooleanField(default=False)
    is_valid = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Signalement de {self.reported.username} par {self.reporter.username}"