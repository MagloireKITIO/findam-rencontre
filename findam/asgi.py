# findam/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from messaging.routing import websocket_urlpatterns as messaging_websocket_urlpatterns
from notifications.routing import websocket_urlpatterns as notifications_websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'findam.settings')

# Initialisation de l'application Django
django_asgi_app = get_asgi_application()

# Configuration du routage des WebSockets
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            messaging_websocket_urlpatterns +
            notifications_websocket_urlpatterns
        )
    ),
})