# messaging/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.serializers import UserSerializer
from .models import Conversation, Message, MessageReceipt, DeletedMessage

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender_details = UserSerializer(source='sender', read_only=True)
    is_sender = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ('id', 'sender', 'sender_details', 'content', 'message_type', 
                 'attachment', 'is_read', 'created_at', 'is_sender')
        read_only_fields = ('id', 'sender', 'is_read', 'created_at')
    
    def get_is_sender(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.sender.id == request.user.id
        return False

class ConversationSerializer(serializers.ModelSerializer):
    participants_details = UserSerializer(source='participants', many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ('id', 'participants', 'participants_details', 'created_at', 
                 'updated_at', 'is_active', 'last_message', 'unread_count', 
                 'other_participant')
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'participants': {'write_only': True}
        }
    
    def get_last_message(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return None
            
        user = request.user
        
        # Récupérer le dernier message qui n'a pas été supprimé par l'utilisateur
        last_message = obj.messages.exclude(
            deleted_by__user=user
        ).order_by('-created_at').first()
        
        if not last_message:
            return None
            
        return {
            'id': last_message.id,
            'content': last_message.content,
            'sender_id': last_message.sender.id,
            'is_read': last_message.is_read,
            'created_at': last_message.created_at
        }
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return 0
            
        user = request.user
        
        # Compter les messages non lus envoyés par les autres participants
        return obj.messages.filter(
            sender__in=obj.participants.exclude(id=user.id),
            is_read=False
        ).exclude(
            deleted_by__user=user
        ).count()
    
    def get_other_participant(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return None
            
        user = request.user
        other_user = obj.get_other_participant(user)
        
        if not other_user:
            return None
            
        return UserSerializer(other_user).data
    
    def create(self, validated_data):
        participants = validated_data.pop('participants')
        conversation = Conversation.objects.create(**validated_data)
        conversation.participants.set(participants)
        return conversation

class CreateMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('id', 'conversation', 'content', 'message_type', 'attachment', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['sender'] = user
        return super().create(validated_data)
    
    def validate_conversation(self, value):
        user = self.context['request'].user
        
        # Vérifier que l'utilisateur est bien un participant de la conversation
        if not value.participants.filter(id=user.id).exists():
            raise serializers.ValidationError(
                "Vous n'êtes pas autorisé à envoyer des messages dans cette conversation."
            )
        
        # Vérifier que la conversation est active
        if not value.is_active:
            raise serializers.ValidationError(
                "Cette conversation n'est plus active."
            )
            
        return value

class MessageReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReceipt
        fields = ('id', 'message', 'recipient', 'status', 'timestamp')
        read_only_fields = ('id', 'timestamp')

class DeletedMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeletedMessage
        fields = ('id', 'message', 'user', 'deleted_at')
        read_only_fields = ('id', 'user', 'deleted_at')
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)