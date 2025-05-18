# subscriptions/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Subscription, Payment

User = get_user_model()

@receiver(post_save, sender=Subscription)
def update_user_premium_status(sender, instance, **kwargs):
    """Met à jour le statut premium de l'utilisateur lorsqu'un abonnement est créé ou modifié"""
    
    if instance.status == 'ACTIVE' and instance.start_date and instance.end_date:
        # Vérifier si l'abonnement est actuellement actif
        now = timezone.now()
        if instance.start_date <= now <= instance.end_date:
            user = instance.user
            user.is_premium = True
            user.premium_until = instance.end_date
            user.save(update_fields=['is_premium', 'premium_until'])

@receiver(post_save, sender=Payment)
def update_subscription_status(sender, instance, **kwargs):
    """Met à jour le statut de l'abonnement lorsqu'un paiement est créé ou modifié"""
    
    if instance.subscription and instance.payment_type == 'SUBSCRIPTION':
        subscription = instance.subscription
        
        if instance.status == 'SUCCESS':
            # Paiement réussi, activer l'abonnement s'il n'est pas déjà actif
            if subscription.status != 'ACTIVE':
                subscription.status = 'ACTIVE'
                subscription.start_date = timezone.now()
                
                # Calculer la date de fin en fonction du plan
                if subscription.plan and subscription.plan.days:
                    subscription.end_date = timezone.now() + timezone.timedelta(days=subscription.plan.days)
                
                subscription.save()
        
        elif instance.status in ['FAILED', 'CANCELLED']:
            # Paiement échoué ou annulé, marquer l'abonnement comme annulé
            if subscription.status == 'PENDING':
                subscription.status = 'CANCELLED'
                subscription.save()