# notifications/views.py

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Notification, NotificationPreference, DeviceToken
from .serializers import (
    NotificationSerializer, NotificationPreferenceSerializer,
    DeviceTokenSerializer, UnregisterDeviceSerializer
)
from .services import NotificationService

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API pour gérer les notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(recipient=user).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Récupérer les notifications non lues"""
        queryset = self.get_queryset().filter(is_read=False)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marquer une notification comme lue"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"status": "success"})
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Marquer toutes les notifications comme lues"""
        count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"status": "success", "count": count})

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """API pour gérer les préférences de notification"""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Récupérer ou créer les préférences de l'utilisateur"""
        obj, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return obj

class RegisterDeviceView(generics.CreateAPIView):
    """API pour enregistrer un appareil pour les notifications push"""
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data.get('token')
        platform = serializer.validated_data.get('platform')
        device_name = serializer.validated_data.get('device_name')
        
        # Utiliser le service pour enregistrer l'appareil
        device_token = NotificationService.register_device(
            user_id=request.user.id,
            token=token,
            platform=platform,
            device_name=device_name
        )
        
        if device_token:
            return Response(
                DeviceTokenSerializer(device_token).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            {"error": "Erreur lors de l'enregistrement de l'appareil"},
            status=status.HTTP_400_BAD_REQUEST
        )

class UnregisterDeviceView(generics.GenericAPIView):
    """API pour désactiver un appareil pour les notifications push"""
    serializer_class = UnregisterDeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data.get('token')
        
        # Utiliser le service pour désactiver l'appareil
        success = NotificationService.unregister_device(token)
        
        if success:
            return Response(
                {"status": "success"},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {"error": "Erreur lors de la désactivation de l'appareil"},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_count(request):
    """Récupérer le nombre de notifications non lues"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return Response({"count": count})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_test_notification(request):
    """Envoyer une notification de test à l'utilisateur"""
    user = request.user
    
    notification = NotificationService.send_notification(
        recipient_id=user.id,
        notification_type='SYSTEM',
        context_type='SYSTEM',
        context_id=0,
        title="Notification de test",
        message="Ceci est une notification de test.",
        action_text="Voir",
        action_url="/profile"
    )
    
    if notification:
        return Response({
            "status": "success",
            "notification": NotificationSerializer(notification).data
        })
    
    return Response(
        {"error": "Erreur lors de l'envoi de la notification"},
        status=status.HTTP_400_BAD_REQUEST
    )