# findam/asgi.py

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

# Importations pour l'authentification JWT
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
from django.contrib.auth import get_user_model

# Importez vos modèles de routage WebSocket
from messaging.routing import websocket_urlpatterns as messaging_websocket_urlpatterns
from notifications.routing import websocket_urlpatterns as notifications_websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'findam.settings')
django.setup()

# Authentification middleware pour les WebSockets
class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Extraire le token de la query string
        query_string = scope.get("query_string", b"").decode()
        query_params = dict(qp.split("=") for qp in query_string.split("&") if "=" in qp)
        token = query_params.get("token", None)
        
        if token:
            try:
                # Décoder le token
                UntypedToken(token)
                decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = decoded_data.get("user_id")
                
                # Obtenir l'utilisateur
                scope["user"] = await self.get_user(user_id)
                print(f"WebSocket authentifié pour l'utilisateur {user_id}")
            except (InvalidToken, TokenError) as e:
                print(f"Erreur d'authentification WebSocket: {e}")
                scope["user"] = None
        else:
            print("Pas de token fourni pour WebSocket")
            scope["user"] = None
            
        return await self.app(scope, receive, send)
    
    @database_sync_to_async
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

# Application ASGI
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            AuthMiddlewareStack(
                URLRouter(
                    messaging_websocket_urlpatterns +
                    notifications_websocket_urlpatterns
                )
            )
        )
    ),
})