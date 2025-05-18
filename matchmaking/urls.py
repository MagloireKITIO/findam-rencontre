# matchmaking/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserDiscoveryView, NearbyUsersView, UserPreferenceViewSet,
    SwipeViewSet, LikeViewSet, DislikeViewSet, MatchViewSet,
    BlockedUserViewSet, ReportViewSet, get_user_stats
)

router = DefaultRouter()
router.register(r'preferences', UserPreferenceViewSet, basename='preference')
router.register(r'swipes', SwipeViewSet, basename='swipe')
router.register(r'likes', LikeViewSet, basename='like')
router.register(r'dislikes', DislikeViewSet, basename='dislike')
router.register(r'matches', MatchViewSet, basename='match')
router.register(r'blocks', BlockedUserViewSet, basename='block')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
    path('discover/', UserDiscoveryView.as_view(), name='discover'),
    path('nearby/', NearbyUsersView.as_view(), name='nearby'),
    path('stats/', get_user_stats, name='stats'),
]