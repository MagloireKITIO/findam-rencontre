# accounts/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

class User(AbstractUser):
    """Modèle utilisateur personnalisé pour Findam"""
    
    GENDER_CHOICES = (
        ('M', 'Homme'),
        ('F', 'Femme'),
        ('O', 'Autre'),
    )
    
    SEEKING_CHOICES = (
        ('M', 'Hommes'),
        ('F', 'Femmes'),
        ('B', 'Les deux'),
    )

    email = models.EmailField(_('adresse email'), unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?237?\d{9}$',
        message="Le numéro doit être au format: '+237xxxxxxxxx'. 9 chiffres maximum."
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=15,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_("Numéro de téléphone")
    )
    is_phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True
    )
    seeking = models.CharField(
        max_length=1,
        choices=SEEKING_CHOICES,
        blank=True
    )
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_premium = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='fr')
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.username

    def get_age(self):
        from datetime import date
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None

class UserProfile(models.Model):
    """Extension du profil utilisateur avec plus de détails"""
    
    EDUCATION_CHOICES = (
        ('HS', 'Lycée'),
        ('UG', 'Licence'),
        ('GD', 'Master'),
        ('PD', 'Doctorat'),
        ('OT', 'Autre'),
    )
    
    RELATIONSHIP_STATUS_CHOICES = (
        ('S', 'Célibataire'),
        ('R', 'En relation'),
        ('E', 'Fiancé(e)'),
        ('M', 'Marié(e)'),
        ('D', 'Divorcé(e)'),
        ('W', 'Veuf/Veuve'),
        ('C', 'Compliqué'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    height = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Taille en cm")
    education = models.CharField(
        max_length=2,
        choices=EDUCATION_CHOICES,
        blank=True
    )
    job_title = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    relationship_status = models.CharField(
        max_length=1,
        choices=RELATIONSHIP_STATUS_CHOICES,
        blank=True
    )
    has_children = models.BooleanField(null=True, blank=True)
    interests = models.TextField(blank=True, help_text="Séparés par des virgules")
    about_me = models.TextField(blank=True)
    looking_for = models.TextField(blank=True)
    
    def __str__(self):
        return f"Profil de {self.user.username}"

class UserPhoto(models.Model):
    """Photos du profil utilisateur"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='profile_pics')
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', '-uploaded_at']
    
    def __str__(self):
        return f"Photo de {self.user.username}"
    
    def save(self, *args, **kwargs):
        # S'assurer qu'il n'y a qu'une seule photo principale
        if self.is_primary:
            UserPhoto.objects.filter(user=self.user, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

class VerificationCode(models.Model):
    """Codes de vérification pour l'authentification"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Code de vérification pour {self.user.username}"
    
    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()

class SocialAccount(models.Model):
    """Comptes sociaux liés à un utilisateur"""
    
    PROVIDER_CHOICES = (
        ('google', 'Google'),
        ('facebook', 'Facebook'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('provider', 'provider_id')
    
    def __str__(self):
        return f"{self.provider} - {self.user.username}"