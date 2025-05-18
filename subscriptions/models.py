# subscriptions/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class SubscriptionPlan(models.Model):
    """Modèle pour les différents plans d'abonnement disponibles"""
    
    DURATION_CHOICES = (
        ('MONTHLY', 'Mensuel'),
        ('BIANNUAL', 'Semestriel'),
        ('ANNUAL', 'Annuel'),
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Prix en FCFA
    features = models.TextField(help_text="Fonctionnalités séparées par des sauts de ligne")
    is_active = models.BooleanField(default=True)
    popular = models.BooleanField(default=False)
    days = models.PositiveIntegerField(help_text="Nombre de jours d'abonnement")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} ({self.get_duration_display()}) - {self.price} FCFA"

class Subscription(models.Model):
    """Modèle pour les abonnements des utilisateurs"""
    
    STATUS_CHOICES = (
        ('PENDING', 'En attente'),
        ('ACTIVE', 'Actif'),
        ('EXPIRED', 'Expiré'),
        ('CANCELLED', 'Annulé'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} - {self.get_status_display()}"
    
    def is_active(self):
        return (
            self.status == 'ACTIVE' and 
            self.start_date is not None and 
            self.end_date is not None and 
            self.start_date <= timezone.now() <= self.end_date
        )

class Payment(models.Model):
    """Modèle pour les paiements effectués"""
    
    STATUS_CHOICES = (
        ('PENDING', 'En attente'),
        ('SUCCESS', 'Réussi'),
        ('FAILED', 'Échoué'),
        ('CANCELLED', 'Annulé'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('CM_MOBILE', 'Mobile Money Cameroun'),
        ('CM_MTN', 'MTN Mobile Money'),
        ('CM_ORANGE', 'Orange Money'),
        ('CARD', 'Carte bancaire'),
        ('PAYPAL', 'PayPal'),
    )
    
    PAYMENT_TYPE_CHOICES = (
        ('SUBSCRIPTION', 'Abonnement'),
        ('EVENT', 'Événement'),
        ('FEATURE', 'Fonctionnalité premium'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(
        Subscription, on_delete=models.SET_NULL, 
        related_name='payments', null=True, blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Montant en FCFA
    reference = models.CharField(max_length=100, unique=True)  # Référence unique pour le paiement
    notchpay_reference = models.CharField(max_length=100, null=True, blank=True)  # Référence Notch Pay
    authorization_url = models.URLField(max_length=500, null=True, blank=True)  # URL de paiement Notch Pay
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    payment_type = models.CharField(max_length=12, choices=PAYMENT_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, null=True, blank=True)  # Pour Mobile Money
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    transaction_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} FCFA - {self.get_status_display()}"

class PaymentCallback(models.Model):
    """Modèle pour stocker les callbacks de paiement reçus"""
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='callbacks')
    raw_data = models.TextField()  # Données brutes du callback
    received_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-received_at']
    
    def __str__(self):
        return f"Callback pour {self.payment.reference} le {self.received_at}"