# messaging/views.py

from django.db.models import Q, Count, Max, F, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Conversation, Message, MessageReceipt, DeletedMessage
from .serializers import (
    ConversationSerializer, MessageSerializer, 
    CreateMessageSerializer, DeletedMessageSerializer
)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class ConversationViewSet(viewsets.ModelViewSet):
    """API pour gérer les conversations"""
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            participants=user,
            is_active=True
        ).order_by('-updated_at')
    
    def perform_create(self, serializer):
        conversation = serializer.save()
        
        # S'assurer que l'utilisateur actuel est un participant
        if not conversation.participants.filter(id=self.request.user.id).exists():
            conversation.participants.add(self.request.user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Récupérer les conversations actives"""
        queryset = self.get_queryset().filter(is_active=True)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Désactiver une conversation"""
        conversation = self.get_object()
        conversation.is_active = False
        conversation.save()
        return Response({"status": "Conversation désactivée"}, status=status.HTTP_200_OK)

class MessageViewSet(viewsets.ModelViewSet):
    """API pour gérer les messages"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMessageSerializer
        return MessageSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Récupérer les messages qui n'ont pas été supprimés par l'utilisateur
        return Message.objects.filter(
            conversation__participants=user
        ).exclude(
            deleted_by__user=user
        ).order_by('created_at')
    
    def list(self, request, *args, **kwargs):
        # Nécessite un paramètre conversation_id
        conversation_id = request.query_params.get('conversation_id')
        if not conversation_id:
            return Response(
                {"error": "Le paramètre conversation_id est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que l'utilisateur est un participant de la conversation
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if not conversation.participants.filter(id=request.user.id).exists():
            return Response(
                {"error": "Vous n'êtes pas autorisé à accéder à cette conversation"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Filtrer les messages par conversation
        queryset = self.get_queryset().filter(conversation_id=conversation_id)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        
        # Mettre à jour la date de dernière activité de la conversation
        conversation = message.conversation
        conversation.save()
        
        # Marquer les messages précédents comme lus
        self.mark_previous_messages_as_read(conversation.id)
    
    def mark_previous_messages_as_read(self, conversation_id):
        """Marquer les messages précédents comme lus"""
        user = self.request.user
        
        Message.objects.filter(
            conversation_id=conversation_id,
            sender__in=Conversation.objects.get(id=conversation_id).participants.exclude(id=user.id),
            is_read=False
        ).update(is_read=True)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marquer un message comme lu"""
        message = self.get_object()
        
        # Ne pas marquer les messages envoyés par l'utilisateur actuel
        if message.sender != request.user:
            message.is_read = True
            message.save()
            
            # Créer un accusé de réception
            MessageReceipt.objects.get_or_create(
                message=message,
                recipient=request.user,
                defaults={'status': 'READ'}
            )
        
        return Response({"status": "Message marqué comme lu"}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def delete_for_me(self, request, pk=None):
        """Supprimer un message pour l'utilisateur actuel"""
        message = self.get_object()
        
        # Créer un enregistrement de suppression
        DeletedMessage.objects.get_or_create(
            message=message,
            user=request.user
        )
        
        return Response({"status": "Message supprimé"}, status=status.HTTP_200_OK)

class CreateConversationView(generics.CreateAPIView):
    """API pour créer une nouvelle conversation"""
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Récupérer l'autre utilisateur
        other_user_id = request.data.get('user_id')
        if not other_user_id:
            return Response(
                {"error": "L'identifiant de l'utilisateur est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier si une conversation existe déjà
        user = request.user
        existing_conversation = Conversation.objects.filter(
            participants=user
        ).filter(
            participants=other_user_id
        ).first()
        
        if existing_conversation:
            serializer = ConversationSerializer(existing_conversation)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Créer une nouvelle conversation
        conversation = Conversation.objects.create()
        conversation.participants.add(user.id, other_user_id)
        
        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_with_user(request, user_id):
    """Récupérer ou créer une conversation avec un utilisateur spécifique"""
    user = request.user
    
    # Vérifier si une conversation existe déjà
    existing_conversation = Conversation.objects.filter(
        participants=user
    ).filter(
        participants=user_id
    ).first()
    
    if existing_conversation:
        serializer = ConversationSerializer(existing_conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    # Créer une nouvelle conversation
    conversation = Conversation.objects.create()
    conversation.participants.add(user.id, user_id)
    
    serializer = ConversationSerializer(conversation, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """Récupérer le nombre de messages non lus"""
    user = request.user
    
    unread_count = Message.objects.filter(
        conversation__participants=user,
        sender__in=Conversation.objects.filter(participants=user).values('participants').exclude(participants=user),
        is_read=False
    ).exclude(
        deleted_by__user=user
    ).count()
    
    return Response({'unread_count': unread_count}, status=status.HTTP_200_OK)