# notifications/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model

from accounts.serializers import UserSerializer
from .models import Notification, NotificationPreference, DeviceToken

User = get_user_model()

class NotificationSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ('id', 'notification_type', 'context_type', 'context_id', 
                 'actor_id', 'actor', 'title', 'message', 'image_url', 
                 'action_url', 'action_text', 'is_read', 'created_at')
        read_only_fields = ('id', 'notification_type', 'context_type', 'context_id', 
                          'actor_id', 'actor', 'title', 'message', 'image_url', 
                          'action_url', 'action_text', 'created_at')
    
    def get_actor(self, obj):
        if obj.actor_id:
            try:
                user = User.objects.get(id=obj.actor_id)
                return {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'profile_picture': user.photos.filter(is_primary=True).first().image.url if user.photos.filter(is_primary=True).exists() else None
                }
            except User.DoesNotExist:
                return None
        return None

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ('id', 'receive_email', 'receive_push', 'matches', 'messages', 
                 'likes', 'events', 'subscription', 'system')
        read_only_fields = ('id',)
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ('id', 'token', 'platform', 'device_name', 'is_active')
        read_only_fields = ('id', 'is_active')
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['is_active'] = True
        
        # Vérifier si le token existe déjà
        token = validated_data.get('token')
        try:
            device_token = DeviceToken.objects.get(token=token)
            # Mettre à jour l'utilisateur et les autres champs
            device_token.user = validated_data['user']
            device_token.platform = validated_data.get('platform', device_token.platform)
            device_token.device_name = validated_data.get('device_name', device_token.device_name)
            device_token.is_active = True
            device_token.save()
            return device_token
        except DeviceToken.DoesNotExist:
            return super().create(validated_data)

class UnregisterDeviceSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    
    def validate_token(self, value):
        try:
            DeviceToken.objects.get(token=value)
            return value
        except DeviceToken.DoesNotExist:
            raise serializers.ValidationError("Token non trouvé.")