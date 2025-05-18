# findam/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('api/matchmaking/', include('matchmaking.urls')),
    path('api/messaging/', include('messaging.urls')),
    path('api/events/', include('events.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/notifications/', include('notifications.urls')),
]

# Ajout des URLs pour servir les fichiers médias en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)