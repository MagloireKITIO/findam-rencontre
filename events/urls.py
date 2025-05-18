# events/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    EventCategoryViewSet, EventViewSet, EventParticipantViewSet,
    EventCommentViewSet, EventSavedViewSet, get_upcoming_events,
    get_popular_events, get_my_events
)

router = DefaultRouter()
router.register(r'categories', EventCategoryViewSet, basename='event-category')
router.register(r'events', EventViewSet, basename='event')
router.register(r'participants', EventParticipantViewSet, basename='event-participant')
router.register(r'comments', EventCommentViewSet, basename='event-comment')
router.register(r'saved', EventSavedViewSet, basename='event-saved')

urlpatterns = [
    path('', include(router.urls)),
    path('upcoming/', get_upcoming_events, name='upcoming-events'),
    path('popular/', get_popular_events, name='popular-events'),
    path('my-events/', get_my_events, name='my-events'),
]