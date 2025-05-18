# events/views.py

from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.pagination import PageNumberPagination

from .models import (
    EventCategory, Event, EventParticipant, 
    EventComment, EventSavedByUser
)
from .serializers import (
    EventCategorySerializer, EventSerializer, EventListSerializer,
    EventParticipantSerializer, EventCommentSerializer,
    EventSavedByUserSerializer
)

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

class EventCategoryViewSet(viewsets.ModelViewSet):
    """API pour gérer les catégories d'événements"""
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def get_queryset(self):
        return EventCategory.objects.all().annotate(
            event_count=Count('events', filter=Q(events__status='PUBLISHED'))
        ).order_by('name')

class EventViewSet(viewsets.ModelViewSet):
    """API pour gérer les événements"""
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        return EventSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = Event.objects.all()
        
        # Filtrer les événements selon leur statut
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        else:
            # Par défaut, ne montrer que les événements publiés aux utilisateurs non-admin
            if not (self.request.user and self.request.user.is_staff):
                queryset = queryset.filter(status='PUBLISHED')
        
        # Filtrer par catégorie
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filtrer par ville
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__iexact=city)
        
        # Filtrer par date
        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(start_date__lte=date_to)
        
        # Filtrer les événements gratuits/payants
        is_free = self.request.query_params.get('is_free')
        if is_free is not None:
            is_free_bool = is_free.lower() == 'true'
            queryset = queryset.filter(is_free=is_free_bool)
        
        # Recherche par mot-clé
        keyword = self.request.query_params.get('keyword')
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(location_name__icontains=keyword)
            )
        
        # Trier les résultats
        ordering = self.request.query_params.get('ordering', '-start_date')
        if ordering:
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def publish(self, request, pk=None):
        """Publier un événement"""
        event = self.get_object()
        event.status = 'PUBLISHED'
        event.save()
        serializer = self.get_serializer(event)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def cancel(self, request, pk=None):
        """Annuler un événement"""
        event = self.get_object()
        event.status = 'CANCELLED'
        event.save()
        serializer = self.get_serializer(event)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def complete(self, request, pk=None):
        """Marquer un événement comme terminé"""
        event = self.get_object()
        event.status = 'COMPLETED'
        event.save()
        serializer = self.get_serializer(event)
        return Response(serializer.data)

class EventParticipantViewSet(viewsets.ModelViewSet):
    """API pour gérer les participants aux événements"""
    serializer_class = EventParticipantSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Les administrateurs peuvent voir tous les participants
        if user.is_staff:
            return EventParticipant.objects.all()
        
        # Les utilisateurs normaux ne peuvent voir que leurs propres participations
        return EventParticipant.objects.filter(user=user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request):
        """S'inscrire à un événement"""
        event_id = request.data.get('event')
        if not event_id:
            return Response(
                {"error": "L'ID de l'événement est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier si l'événement existe et est ouvert à l'inscription
        try:
            event = Event.objects.get(id=event_id, status='PUBLISHED')
        except Event.DoesNotExist:
            return Response(
                {"error": "Événement non trouvé ou non disponible pour inscription"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier si l'inscription est encore possible
        if event.registration_required and event.registration_deadline:
            if timezone.now() > event.registration_deadline:
                return Response(
                    {"error": "La date limite d'inscription est dépassée"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Vérifier si le nombre maximum de participants est atteint
        if event.max_participants:
            if event.participants.count() >= event.max_participants:
                return Response(
                    {"error": "Nombre maximum de participants atteint"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Vérifier si l'utilisateur est déjà inscrit
        if EventParticipant.objects.filter(event=event, user=request.user).exists():
            return Response(
                {"error": "Vous êtes déjà inscrit à cet événement"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer l'inscription
        participant = EventParticipant.objects.create(
            event=event,
            user=request.user,
            status='REGISTERED'
        )
        
        serializer = self.get_serializer(participant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel_registration(self, request, pk=None):
        """Annuler sa participation à un événement"""
        participant = self.get_object()
        
        # Vérifier que l'utilisateur est bien le participant
        if participant.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "Vous n'êtes pas autorisé à annuler cette inscription"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        participant.status = 'CANCELLED'
        participant.save()
        
        serializer = self.get_serializer(participant)
        return Response(serializer.data)

class EventCommentViewSet(viewsets.ModelViewSet):
    """API pour gérer les commentaires sur les événements"""
    serializer_class = EventCommentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = EventComment.objects.all()
        
        # Filtrer par événement
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class EventSavedViewSet(viewsets.ModelViewSet):
    """API pour gérer les événements sauvegardés"""
    serializer_class = EventSavedByUserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return EventSavedByUser.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_save(self, request):
        """Ajouter/Retirer un événement des favoris"""
        event_id = request.data.get('event')
        if not event_id:
            return Response(
                {"error": "L'ID de l'événement est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier si l'événement existe
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response(
                {"error": "Événement non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérifier si l'événement est déjà sauvegardé
        saved = EventSavedByUser.objects.filter(event=event, user=request.user)
        
        if saved.exists():
            # Supprimer si déjà sauvegardé
            saved.delete()
            return Response({"status": "removed"}, status=status.HTTP_200_OK)
        else:
            # Sauvegarder
            saved = EventSavedByUser.objects.create(event=event, user=request.user)
            serializer = self.get_serializer(saved)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_upcoming_events(request):
    """Récupérer les prochains événements"""
    today = timezone.now()
    events = Event.objects.filter(
        status='PUBLISHED',
        start_date__gte=today
    ).order_by('start_date')[:10]
    
    serializer = EventListSerializer(events, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def get_popular_events(request):
    """Récupérer les événements populaires (avec le plus de participants)"""
    events = Event.objects.filter(
        status='PUBLISHED'
    ).annotate(
        participant_count=Count('participants')
    ).order_by('-participant_count')[:10]
    
    serializer = EventListSerializer(events, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_events(request):
    """Récupérer les événements auxquels l'utilisateur participe"""
    participations = EventParticipant.objects.filter(
        user=request.user
    ).exclude(
        status='CANCELLED'
    ).select_related('event')
    
    events = [p.event for p in participations]
    
    serializer = EventListSerializer(events, many=True, context={'request': request})
    return Response(serializer.data)