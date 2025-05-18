# accounts/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    UserViewSet, RegisterView, PhoneVerificationView, 
    VerifyPhoneCodeView, SocialAuthView, UserPhotoViewSet,
    get_verification_status
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'photos', UserPhotoViewSet, basename='user-photo')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-phone/', PhoneVerificationView.as_view(), name='verify-phone'),
    path('verify-code/', VerifyPhoneCodeView.as_view(), name='verify-code'),
    path('social-auth/', SocialAuthView.as_view(), name='social-auth'),
    path('verification-status/', get_verification_status, name='verification-status'),
]