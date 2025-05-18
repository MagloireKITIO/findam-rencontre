# matchmaking/views.py

from datetime import date
from django.db.models import Q, F, Value, IntegerField, Case, When, BooleanField
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import (
    Like, Dislike, Match, BlockedUser, 
    SwipeAction, UserPreference, Report
)
from .serializers import (
    LikeSerializer, DislikeSerializer, MatchSerializer,
    BlockedUserSerializer, SwipeActionSerializer,
    UserPreferenceSerializer, ReportSerializer,
    UserDiscoverySerializer
)

User = get_user_model()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class UserDiscoveryView(generics.ListAPIView):
    """API pour découvrir des utilisateurs potentiels"""
    serializer_class = UserDiscoverySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        
        # Obtenir les préférences de l'utilisateur
        try:
            preferences = user.preferences
        except UserPreference.DoesNotExist:
            # Créer des préférences par défaut si elles n'existent pas
            preferences = UserPreference.objects.create(user=user)
        
        # Calculer l'âge minimum et maximum basé sur les préférences
        today = date.today()
        min_birth_date = date(
            today.year - preferences.max_age - 1,
            today.month,
            today.day
        )
        max_birth_date = date(
            today.year - preferences.min_age,
            today.month,
            today.day
        )
        
        # Récupérer les utilisateurs déjà likés ou dislikés
        liked_users = Like.objects.filter(liker=user).values_list('liked_id', flat=True)
        disliked_users = Dislike.objects.filter(disliker=user).values_list('disliked_id', flat=True)
        
        # Récupérer les utilisateurs bloqués ou qui ont bloqué l'utilisateur
        blocked_users = BlockedUser.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker_id', 'blocked_id')
        
        blocked_ids = set()
        for blocker_id, blocked_id in blocked_users:
            blocked_ids.add(blocker_id)
            blocked_ids.add(blocked_id)
        
        # Exclure l'utilisateur actuel
        blocked_ids.add(user.id)
        
        # Construire la requête
        queryset = User.objects.filter(
            Q(date_of_birth__gte=min_birth_date) & 
            Q(date_of_birth__lte=max_birth_date)
        ).exclude(
            Q(id__in=liked_users) | 
            Q(id__in=disliked_users) | 
            Q(id__in=blocked_ids)
        )
        
        # Filtrer par genre selon les préférences
        if user.seeking == 'M':
            queryset = queryset.filter(gender='M')
        elif user.seeking == 'F':
            queryset = queryset.filter(gender='F')
        
        # Filtrer par vérification si nécessaire
        if preferences.show_verified_only:
            queryset = queryset.filter(is_verified=True)
        
        # Filtrer par profil complet
        queryset = queryset.filter(is_complete=True)
        
        # Ordonner par dernière activité
        queryset = queryset.order_by('-last_active')
        
        return queryset

class NearbyUsersView(generics.ListAPIView):
    """API pour découvrir des utilisateurs à proximité"""
    serializer_class = UserDiscoverySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        
        # Vérifier si l'utilisateur a des coordonnées
        if not user.latitude or not user.longitude:
            return User.objects.none()
        
        # Obtenir les préférences de l'utilisateur pour la distance
        try:
            preferences = user.preferences
            distance = preferences.distance
        except UserPreference.DoesNotExist:
            distance = 50  # Valeur par défaut
        
        # Récupérer les utilisateurs bloqués ou qui ont bloqué l'utilisateur
        blocked_users = BlockedUser.objects.filter(
            Q(blocker=user) | Q(blocked=user)
        ).values_list('blocker_id', 'blocked_id')
        
        blocked_ids = set()
        for blocker_id, blocked_id in blocked_users:
            blocked_ids.add(blocker_id)
            blocked_ids.add(blocked_id)
        
        # Exclure l'utilisateur actuel
        blocked_ids.add(user.id)
        
        # Filtrer par genre selon les préférences
        gender_filter = Q()
        if user.seeking == 'M':
            gender_filter = Q(gender='M')
        elif user.seeking == 'F':
            gender_filter = Q(gender='F')
        
        # Filtrer par vérification si nécessaire
        verified_filter = Q()
        try:
            if user.preferences.show_verified_only:
                verified_filter = Q(is_verified=True)
        except UserPreference.DoesNotExist:
            pass
        
        # Requête pour obtenir tous les utilisateurs avec coordonnées
        queryset = User.objects.filter(
            ~Q(id__in=blocked_ids) & 
            Q(latitude__isnull=False) & 
            Q(longitude__isnull=False) & 
            Q(is_complete=True) & 
            gender_filter & 
            verified_filter
        )
        
        # La distance exacte sera calculée dans le serializer
        return queryset.order_by('-last_active')

class UserPreferenceViewSet(viewsets.ModelViewSet):
    """API pour gérer les préférences utilisateur"""
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        # Obtenir ou créer les préférences de l'utilisateur
        obj, created = UserPreference.objects.get_or_create(user=self.request.user)
        return obj

class SwipeViewSet(viewsets.ModelViewSet):
    """API pour gérer les actions de swipe"""
    serializer_class = SwipeActionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SwipeAction.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class LikeViewSet(viewsets.ModelViewSet):
    """API pour gérer les likes"""
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Like.objects.filter(liker=self.request.user)
    
    @action(detail=False, methods=['get'])
    def received(self, request):
        """Récupérer les likes reçus"""
        received_likes = Like.objects.filter(liked=request.user)
        page = self.paginate_queryset(received_likes)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(received_likes, many=True)
        return Response(serializer.data)

class DislikeViewSet(viewsets.ModelViewSet):
    """API pour gérer les dislikes"""
    serializer_class = DislikeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Dislike.objects.filter(disliker=self.request.user)

class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    """API pour gérer les matchs"""
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Match.objects.filter(
            Q(user1=user) | Q(user2=user),
            is_active=True
        )
    
    @action(detail=True, methods=['post'])
    def unmatch(self, request, pk=None):
        """Désactiver un match"""
        match = self.get_object()
        match.is_active = False
        match.save()
        return Response({"status": "Match désactivé"}, status=status.HTTP_200_OK)

class BlockedUserViewSet(viewsets.ModelViewSet):
    """API pour gérer les utilisateurs bloqués"""
    serializer_class = BlockedUserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BlockedUser.objects.filter(blocker=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(blocker=self.request.user)

class ReportViewSet(viewsets.ModelViewSet):
    """API pour gérer les signalements"""
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Report.objects.filter(reporter=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_stats(request):
    """Récupérer les statistiques de l'utilisateur"""
    user = request.user
    
    # Compter les likes, matchs, etc.
    likes_given = Like.objects.filter(liker=user).count()
    likes_received = Like.objects.filter(liked=user).count()
    matches_count = Match.objects.filter(
        Q(user1=user) | Q(user2=user),
        is_active=True
    ).count()
    
    return Response({
        'likes_given': likes_given,
        'likes_received': likes_received,
        'matches': matches_count
    }, status=status.HTTP_200_OK)