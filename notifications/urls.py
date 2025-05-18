# notifications/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet, NotificationPreferenceViewSet,
    RegisterDeviceView, UnregisterDeviceView,
    get_notification_count, send_test_notification
)

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'preferences', NotificationPreferenceViewSet, basename='notification-preference')

urlpatterns = [
    path('', include(router.urls)),
    path('register-device/', RegisterDeviceView.as_view(), name='register-device'),
    path('unregister-device/', UnregisterDeviceView.as_view(), name='unregister-device'),
    path('count/', get_notification_count, name='notification-count'),
    path('test/', send_test_notification, name='send-test-notification'),
]