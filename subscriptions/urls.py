# subscriptions/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SubscriptionPlanViewSet, SubscriptionViewSet, PaymentViewSet,
    InitiatePaymentView, VerifyPaymentView, CancelSubscriptionView,
    payment_callback, subscription_status
)

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('initiate-payment/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='verify-payment'),
    path('cancel-subscription/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('payment-callback/', payment_callback, name='payment-callback'),
    path('status/', subscription_status, name='subscription-status'),
]