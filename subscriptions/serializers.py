# subscriptions/serializers.py

from rest_framework import serializers
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth import get_user_model

from .models import SubscriptionPlan, Subscription, Payment, PaymentCallback
from .services import NotchPayService

User = get_user_model()

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    subscriber_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'name', 'description', 'duration', 'price', 'features', 
                 'days', 'is_active', 'popular', 'subscriber_count')
    
    def get_subscriber_count(self, obj):
        return obj.subscriptions.filter(status='ACTIVE').count()
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Convertir les fonctionnalités en liste
        if 'features' in data and data['features']:
            data['features'] = [feature.strip() for feature in data['features'].split('\n') if feature.strip()]
        return data

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    is_currently_active = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = ('id', 'user', 'plan', 'plan_details', 'start_date', 'end_date', 
                 'status', 'auto_renew', 'created_at', 'is_currently_active', 'days_left')
        read_only_fields = ('id', 'user', 'start_date', 'end_date', 'status', 
                          'created_at', 'is_currently_active', 'days_left')
    
    def get_is_currently_active(self, obj):
        return obj.is_active()
    
    def get_days_left(self, obj):
        if obj.is_active() and obj.end_date:
            days = (obj.end_date - timezone.now()).days
            return max(0, days)
        return 0

class PaymentSerializer(serializers.ModelSerializer):
    subscription_details = SubscriptionSerializer(source='subscription', read_only=True)
    
    class Meta:
        model = Payment
        fields = ('id', 'user', 'subscription', 'subscription_details', 'amount', 
                 'reference', 'notchpay_reference', 'authorization_url', 
                 'payment_method', 'payment_type', 'phone_number', 'status', 
                 'transaction_date', 'created_at')
        read_only_fields = ('id', 'user', 'reference', 'notchpay_reference', 
                          'authorization_url', 'status', 'transaction_date', 'created_at')

class InitiatePaymentSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPlan.objects.filter(is_active=True))
    payment_method = serializers.ChoiceField(choices=Payment.PAYMENT_METHOD_CHOICES)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        payment_method = attrs.get('payment_method')
        phone_number = attrs.get('phone_number')
        
        # Vérifier que le numéro de téléphone est fourni pour Mobile Money
        if payment_method in ['CM_MOBILE', 'CM_MTN', 'CM_ORANGE'] and not phone_number:
            raise serializers.ValidationError(
                {"phone_number": "Le numéro de téléphone est requis pour le paiement mobile."}
            )
        
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        plan = validated_data.get('plan')
        payment_method = validated_data.get('payment_method')
        phone_number = validated_data.get('phone_number', '')
        
        # Créer une nouvelle souscription
        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            status='PENDING'
        )
        
        # Générer une référence de paiement
        payment_reference = NotchPayService.generate_payment_reference()
        
        # Créer un enregistrement de paiement
        payment = Payment.objects.create(
            user=user,
            subscription=subscription,
            amount=plan.price,
            reference=payment_reference,
            payment_method=payment_method,
            payment_type='SUBSCRIPTION',
            phone_number=phone_number,
            status='PENDING'
        )
        
        # Initialiser le paiement avec Notch Pay
        notchpay_service = NotchPayService()
        description = f"Abonnement {plan.get_duration_display()} Findam"
        
        payment_response = notchpay_service.initialize_payment(
            user=user,
            amount=float(plan.price),
            payment_reference=payment_reference,
            payment_type='SUBSCRIPTION',
            description=description
        )
        
        if 'error' in payment_response:
            # Échec de l'initialisation du paiement
            payment.status = 'FAILED'
            payment.save()
            
            # Mettre à jour la souscription
            subscription.status = 'CANCELLED'
            subscription.save()
            
            raise serializers.ValidationError(
                {"payment": f"Échec de l'initialisation du paiement: {payment_response.get('message', 'Erreur inconnue')}"}
            )
        
        # Mettre à jour le paiement avec les informations de Notch Pay
        transaction_data = payment_response.get('transaction', {})
        payment.notchpay_reference = transaction_data.get('reference')
        payment.authorization_url = payment_response.get('authorization_url')
        payment.save()
        
        # Si c'est un paiement mobile, le traiter immédiatement
        if payment_method in ['CM_MOBILE', 'CM_MTN', 'CM_ORANGE']:
            channel = 'cm.mobile'
            if payment_method == 'CM_MTN':
                channel = 'cm.mtn'
            elif payment_method == 'CM_ORANGE':
                channel = 'cm.orange'
            
            mobile_response = notchpay_service.process_mobile_payment(
                payment_reference=payment_reference,
                phone_number=phone_number,
                channel=channel
            )
            
            if 'error' in mobile_response:
                # Échec du traitement du paiement mobile
                payment.status = 'FAILED'
                payment.save()
                
                # Mettre à jour la souscription
                subscription.status = 'CANCELLED'
                subscription.save()
                
                raise serializers.ValidationError(
                    {"payment": f"Échec du traitement du paiement mobile: {mobile_response.get('message', 'Erreur inconnue')}"}
                )
        
        return payment

class VerifyPaymentSerializer(serializers.Serializer):
    payment_reference = serializers.CharField()
    
    def validate(self, attrs):
        payment_reference = attrs.get('payment_reference')
        
        try:
            payment = Payment.objects.get(reference=payment_reference)
            attrs['payment'] = payment
        except Payment.DoesNotExist:
            raise serializers.ValidationError(
                {"payment_reference": "Paiement non trouvé."}
            )
        
        return attrs

class CancelSubscriptionSerializer(serializers.Serializer):
    subscription_id = serializers.IntegerField()
    
    def validate(self, attrs):
        subscription_id = attrs.get('subscription_id')
        user = self.context['request'].user
        
        try:
            subscription = Subscription.objects.get(id=subscription_id, user=user)
            attrs['subscription'] = subscription
        except Subscription.DoesNotExist:
            raise serializers.ValidationError(
                {"subscription_id": "Abonnement non trouvé."}
            )
        
        return attrs