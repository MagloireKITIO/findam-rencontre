# events/serializers.py

from rest_framework import serializers
from django.utils import timezone
from django.db.models import Avg
from django.contrib.auth import get_user_model

from accounts.serializers import UserSerializer
from .models import EventCategory, Event, EventParticipant, EventComment, EventSavedByUser

User = get_user_model()

class EventCategorySerializer(serializers.ModelSerializer):
    event_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EventCategory
        fields = ('id', 'name', 'description', 'icon', 'event_count')
    
    def get_event_count(self, obj):
        return obj.events.filter(status='PUBLISHED').count()

class EventSerializer(serializers.ModelSerializer):
    category_details = EventCategorySerializer(source='category', read_only=True)
    created_by_details = UserSerializer(source='created_by', read_only=True)
    is_saved = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = ('id', 'title', 'description', 'category', 'category_details', 'image',
                 'location_name', 'address', 'city', 'latitude', 'longitude',
                 'start_date', 'end_date', 'price', 'is_free', 'max_participants',
                 'registration_required', 'registration_deadline', 'status',
                 'created_by', 'created_by_details', 'created_at', 'updated_at',
                 'is_saved', 'is_registered', 'participant_count')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at', 'status')
    
    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return EventSavedByUser.objects.filter(event=obj, user=request.user).exists()
        return False
    
    def get_is_registered(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return EventParticipant.objects.filter(event=obj, user=request.user).exists()
        return False
    
    def get_participant_count(self, obj):
        return obj.participants.count()
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['status'] = 'DRAFT'  # Par défaut, les événements sont créés en brouillon
        return super().create(validated_data)

class EventListSerializer(serializers.ModelSerializer):
    """Serializer léger pour les listes d'événements"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_saved = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = ('id', 'title', 'image', 'category_name', 'location_name', 'city',
                 'start_date', 'is_free', 'price', 'status', 'is_saved', 'participant_count')
    
    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return EventSavedByUser.objects.filter(event=obj, user=request.user).exists()
        return False
    
    def get_participant_count(self, obj):
        return obj.participants.count()

class EventParticipantSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    event_details = EventListSerializer(source='event', read_only=True)
    
    class Meta:
        model = EventParticipant
        fields = ('id', 'event', 'event_details', 'user', 'user_details',
                 'status', 'registration_date', 'notes')
        read_only_fields = ('id', 'user', 'registration_date')
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class EventCommentSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = EventComment
        fields = ('id', 'event', 'user', 'user_details', 'content', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class EventSavedByUserSerializer(serializers.ModelSerializer):
    event_details = EventListSerializer(source='event', read_only=True)
    
    class Meta:
        model = EventSavedByUser
        fields = ('id', 'event', 'event_details', 'user', 'saved_at')
        read_only_fields = ('id', 'user', 'saved_at')
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)