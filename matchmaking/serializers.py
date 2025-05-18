# matchmaking/serializers.py

import math
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

from accounts.serializers import UserSerializer
from .models import (
    Like, Dislike, Match, BlockedUser, 
    SwipeAction, UserPreference, Report
)

User = get_user_model()

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ('min_age', 'max_age', 'distance', 'show_verified_only')
        
    def create(self, validated_data):
        user = self.context['request'].user
        return UserPreference.objects.create(user=user, **validated_data)

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ('id', 'liker', 'liked', 'created_at')
        read_only_fields = ('id', 'liker', 'created_at')
        
    def create(self, validated_data):
        validated_data['liker'] = self.context['request'].user
        return super().create(validated_data)

class DislikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dislike
        fields = ('id', 'disliker', 'disliked', 'created_at')
        read_only_fields = ('id', 'disliker', 'created_at')
        
    def create(self, validated_data):
        validated_data['disliker'] = self.context['request'].user
        return super().create(validated_data)

class MatchSerializer(serializers.ModelSerializer):
    user1 = UserSerializer(read_only=True)
    user2 = UserSerializer(read_only=True)
    
    class Meta:
        model = Match
        fields = ('id', 'user1', 'user2', 'created_at', 'is_active')
        read_only_fields = ('id', 'user1', 'user2', 'created_at')

class BlockedUserSerializer(serializers.ModelSerializer):
    blocked_user = UserSerializer(source='blocked', read_only=True)
    
    class Meta:
        model = BlockedUser
        fields = ('id', 'blocked', 'blocked_user', 'reason', 'created_at')
        read_only_fields = ('id', 'blocker', 'created_at')
        extra_kwargs = {
            'blocked': {'write_only': True}
        }
        
    def create(self, validated_data):
        validated_data['blocker'] = self.context['request'].user
        return super().create(validated_data)

class ReportSerializer(serializers.ModelSerializer):
    reported_user = UserSerializer(source='reported', read_only=True)
    
    class Meta:
        model = Report
        fields = ('id', 'reported', 'reported_user', 'reason', 'details', 'created_at')
        read_only_fields = ('id', 'reporter', 'created_at')
        extra_kwargs = {
            'reported': {'write_only': True}
        }
        
    def create(self, validated_data):
        validated_data['reporter'] = self.context['request'].user
        return super().create(validated_data)

class SwipeActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwipeAction
        fields = ('id', 'target', 'action', 'created_at')
        read_only_fields = ('id', 'user', 'created_at')
        
    def create(self, validated_data):
        user = self.context['request'].user
        target = validated_data.get('target')
        action = validated_data.get('action')
        
        # Vérifier si l'utilisateur est bloqué
        if BlockedUser.objects.filter(
            Q(blocker=user, blocked=target) | Q(blocker=target, blocked=user)
        ).exists():
            raise serializers.ValidationError({"error": "Action impossible: l'un des utilisateurs a bloqué l'autre."})
        
        # Créer l'action de swipe
        swipe_action = SwipeAction.objects.create(
            user=user,
            target=target,
            action=action
        )
        
        # Si c'est un like, créer un like et vérifier le match potentiel
        if action == 'L' or action == 'S':
            Like.objects.get_or_create(liker=user, liked=target)
            
            # Vérifier s'il y a un match
            if Like.objects.filter(liker=target, liked=user).exists():
                # Créer un match si ce n'est pas déjà fait
                Match.objects.get_or_create(
                    user1=min(user, target, key=lambda u: u.id),
                    user2=max(user, target, key=lambda u: u.id),
                    defaults={'is_active': True}
                )
        
        # Si c'est un dislike, créer un dislike
        elif action == 'D':
            Dislike.objects.get_or_create(disliker=user, disliked=target)
        
        return swipe_action

class UserDiscoverySerializer(UserSerializer):
    distance = serializers.SerializerMethodField()
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('distance',)
    
    def get_distance(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.latitude and request.user.longitude:
            return self.calculate_distance(
                request.user.latitude, request.user.longitude,
                obj.latitude, obj.longitude
            )
        return None
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        if not all([lat1, lon1, lat2, lon2]):
            return None
            
        # Rayon de la Terre en km
        R = 6371
        
        # Conversion en radians
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)
        
        # Différence de longitude et latitude
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        # Formule de Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return round(distance, 1)