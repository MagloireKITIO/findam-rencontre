# subscriptions/views.py

import json
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.pagination import PageNumberPagination
from datetime import timedelta

from .models import SubscriptionPlan, Subscription, Payment, PaymentCallback
from .serializers import (
    SubscriptionPlanSerializer, SubscriptionSerializer, 
    PaymentSerializer, InitiatePaymentSerializer,
    VerifyPaymentSerializer, CancelSubscriptionSerializer
)
from .services import NotchPayService

class IsAdminOrReadOnly(permissions.BasePermission):
    """Permission personnalisée pour permettre uniquement aux administrateurs de modifier"""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """API pour gérer les plans d'abonnement"""
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        queryset = SubscriptionPlan.objects.all()
        
        # Par défaut, ne montrer que les plans actifs aux utilisateurs non-admin
        if not (self.request.user and self.request.user.is_staff):
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('price')

class SubscriptionViewSet(viewsets.ModelViewSet):
    """API pour gérer les abonnements"""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Les administrateurs peuvent voir tous les abonnements
        if user.is_staff:
            return Subscription.objects.all()
        
        # Les utilisateurs normaux ne peuvent voir que leurs propres abonnements
        return Subscription.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Récupérer l'abonnement actif de l'utilisateur"""
        user = request.user
        
        # Rechercher l'abonnement actif
        active_subscription = Subscription.objects.filter(
            user=user,
            status='ACTIVE',
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).first()
        
        if active_subscription:
            serializer = self.get_serializer(active_subscription)
            return Response(serializer.data)
        else:
            return Response(
                {"message": "Aucun abonnement actif"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler un abonnement"""
        subscription = self.get_object()
        
        # Vérifier que l'utilisateur est le propriétaire de l'abonnement
        if subscription.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "Vous n'êtes pas autorisé à annuler cet abonnement"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Désactiver le renouvellement automatique
        subscription.auto_renew = False
        subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """API pour consulter les paiements"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        
        # Les administrateurs peuvent voir tous les paiements
        if user.is_staff:
            return Payment.objects.all()
        
        # Les utilisateurs normaux ne peuvent voir que leurs propres paiements
        return Payment.objects.filter(user=user)

class InitiatePaymentView(generics.GenericAPIView):
    """API pour initier un paiement"""
    serializer_class = InitiatePaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            payment = serializer.save()
            
            return Response({
                "message": "Paiement initié avec succès",
                "payment": {
                    "id": payment.id,
                    "reference": payment.reference,
                    "amount": payment.amount,
                    "status": payment.status,
                    "authorization_url": payment.authorization_url
                }
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

class VerifyPaymentView(generics.GenericAPIView):
    """API pour vérifier le statut d'un paiement"""
    serializer_class = VerifyPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment = serializer.validated_data['payment']
        
        # Vérifier que l'utilisateur est le propriétaire du paiement
        if payment.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "Vous n'êtes pas autorisé à vérifier ce paiement"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier le statut du paiement via l'API Notch Pay
        notchpay_service = NotchPayService()
        payment_status = notchpay_service.verify_payment(payment.reference)
        
        if 'error' in payment_status:
            return Response(
                {"error": f"Erreur lors de la vérification du paiement: {payment_status.get('message', 'Erreur inconnue')}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mettre à jour le statut du paiement
        transaction_data = payment_status.get('transaction', {})
        payment_status_value = transaction_data.get('status')
        
        if payment_status_value == 'success':
            # Paiement réussi
            payment.status = 'SUCCESS'
            payment.transaction_date = timezone.now()
            payment.save()
            
            # Activer l'abonnement
            if payment.subscription:
                subscription = payment.subscription
                subscription.status = 'ACTIVE'
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timedelta(days=subscription.plan.days)
                subscription.save()
                
                # Mettre à jour le statut premium de l'utilisateur
                user = payment.user
                user.is_premium = True
                user.premium_until = subscription.end_date
                user.save()
        
        elif payment_status_value == 'failed':
            # Paiement échoué
            payment.status = 'FAILED'
            payment.save()
            
            # Annuler l'abonnement
            if payment.subscription:
                payment.subscription.status = 'CANCELLED'
                payment.subscription.save()
        
        elif payment_status_value == 'cancelled':
            # Paiement annulé
            payment.status = 'CANCELLED'
            payment.save()
            
            # Annuler l'abonnement
            if payment.subscription:
                payment.subscription.status = 'CANCELLED'
                payment.subscription.save()
        
        return Response({
            "payment": {
                "id": payment.id,
                "reference": payment.reference,
                "status": payment.status,
                "transaction_date": payment.transaction_date
            },
            "notchpay_status": payment_status_value
        })

class CancelSubscriptionView(generics.GenericAPIView):
    """API pour annuler un abonnement"""
    serializer_class = CancelSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        subscription = serializer.validated_data['subscription']
        
        # Désactiver le renouvellement automatique
        subscription.auto_renew = False
        subscription.save()
        
        return Response({
            "message": "Le renouvellement automatique a été désactivé",
            "subscription": {
                "id": subscription.id,
                "status": subscription.status,
                "auto_renew": subscription.auto_renew
            }
        })

@api_view(['POST'])
@permission_classes([AllowAny])
def payment_callback(request):
    """Webhook pour recevoir les callbacks de Notch Pay"""
    
    # Récupérer les données du callback
    try:
        data = json.loads(request.body)
        
        # Récupérer la référence de paiement
        reference = data.get('reference') or data.get('trxref')
        
        if not reference:
            return HttpResponse(status=400)
        
        # Récupérer le paiement correspondant
        try:
            payment = Payment.objects.get(reference=reference)
            
            # Enregistrer le callback
            PaymentCallback.objects.create(
                payment=payment,
                raw_data=json.dumps(data)
            )
            
            # Vérifier le statut du paiement
            status_value = data.get('status')
            
            if status_value == 'success':
                # Paiement réussi
                payment.status = 'SUCCESS'
                payment.transaction_date = timezone.now()
                payment.save()
                
                # Activer l'abonnement
                if payment.subscription:
                    subscription = payment.subscription
                    subscription.status = 'ACTIVE'
                    subscription.start_date = timezone.now()
                    subscription.end_date = timezone.now() + timedelta(days=subscription.plan.days)
                    subscription.save()
                    
                    # Mettre à jour le statut premium de l'utilisateur
                    user = payment.user
                    user.is_premium = True
                    user.premium_until = subscription.end_date
                    user.save()
            
            elif status_value == 'failed':
                # Paiement échoué
                payment.status = 'FAILED'
                payment.save()
                
                # Annuler l'abonnement
                if payment.subscription:
                    payment.subscription.status = 'CANCELLED'
                    payment.subscription.save()
            
            elif status_value == 'cancelled':
                # Paiement annulé
                payment.status = 'CANCELLED'
                payment.save()
                
                # Annuler l'abonnement
                if payment.subscription:
                    payment.subscription.status = 'CANCELLED'
                    payment.subscription.save()
            
            return HttpResponse(status=200)
        
        except Payment.DoesNotExist:
            return HttpResponse(status=404)
    
    except json.JSONDecodeError:
        return HttpResponse(status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    """Récupérer le statut d'abonnement de l'utilisateur"""
    user = request.user
    
    # Vérifier si l'utilisateur a un abonnement actif
    active_subscription = Subscription.objects.filter(
        user=user,
        status='ACTIVE',
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    ).first()
    
    if active_subscription:
        days_left = (active_subscription.end_date - timezone.now()).days
        days_left = max(0, days_left)
        
        return Response({
            "is_premium": True,
            "subscription": {
                "id": active_subscription.id,
                "plan": active_subscription.plan.name,
                "end_date": active_subscription.end_date,
                "days_left": days_left,
                "auto_renew": active_subscription.auto_renew
            }
        })
    else:
        return Response({
            "is_premium": False,
            "message": "Aucun abonnement actif",
            "plans": SubscriptionPlanSerializer(
                SubscriptionPlan.objects.filter(is_active=True),
                many=True,
                context={'request': request}
            ).data
        })