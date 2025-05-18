# messaging/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet, MessageViewSet, 
    CreateConversationView, get_conversation_with_user,
    get_unread_count
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
    path('create-conversation/', CreateConversationView.as_view(), name='create-conversation'),
    path('conversation-with-user/<int:user_id>/', get_conversation_with_user, name='conversation-with-user'),
    path('unread-count/', get_unread_count, name='unread-count'),
]