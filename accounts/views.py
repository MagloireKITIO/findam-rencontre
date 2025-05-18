# accounts/views.py

from django.contrib.auth import get_user_model
from django.utils import timezone
import requests
import json
import random
import string
from datetime import timedelta

from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser

from .models import UserPhoto, VerificationCode, SocialAccount
from .serializers import (
    UserSerializer, RegisterSerializer, PhoneVerificationSerializer,
    VerifyPhoneCodeSerializer, SocialAuthSerializer, ChangePasswordSerializer,
    UserPhotoSerializer
)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """API endpoint pour la gestion des utilisateurs"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def update_location(self, request):
        user = request.user
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude is None or longitude is None:
            return Response(
                {"error": "Les coordonnées sont requises"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.latitude = latitude
        user.longitude = longitude
        user.save(update_fields=['latitude', 'longitude'])
        
        return Response(
            {"success": "Localisation mise à jour avec succès"},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": "Mot de passe incorrect"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response(
                {"success": "Mot de passe changé avec succès"},
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(generics.CreateAPIView):
    """API endpoint pour l'inscription utilisateur"""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

class PhoneVerificationView(generics.GenericAPIView):
    """API endpoint pour demander une vérification par téléphone"""
    serializer_class = PhoneVerificationSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']
        user = request.user
        user.phone_number = phone_number
        user.save()
        
        code = serializer.create_verification_code(user)
        
        # Envoi SMS via un service externe (exemple avec une API fictive)
        sms_sent = self.send_verification_sms(phone_number, code)
        
        if sms_sent:
            return Response(
                {"message": "Code de vérification envoyé avec succès"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Échec de l'envoi du SMS"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def send_verification_sms(self, phone_number, code):
        sms_api_url = "https://api.sms.service.cm/send"
        sms_api_key = "votre_api_key"  # À configurer dans settings.py
        
        try:
            response = requests.post(
                sms_api_url,
                json={
                    "to": phone_number,
                    "message": f"Votre code de vérification Findam est: {code}",
                    "api_key": sms_api_key
                }
            )
            
            return response.status_code == 200
        except Exception:
            return False

class VerifyPhoneCodeView(generics.GenericAPIView):
    """API endpoint pour vérifier un code reçu par SMS"""
    serializer_class = VerifyPhoneCodeSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Récupérer l'utilisateur et le code de vérification
        user = serializer.user
        verification = serializer.verification
        
        # Marquer le code comme utilisé
        verification.is_used = True
        verification.save()
        
        # Marquer le téléphone comme vérifié
        user.is_phone_verified = True
        user.save()
        
        return Response(
            {"message": "Numéro de téléphone vérifié avec succès"},
            status=status.HTTP_200_OK
        )

class SocialAuthView(generics.GenericAPIView):
    """API endpoint pour l'authentification via réseaux sociaux"""
    serializer_class = SocialAuthSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_info = serializer.user_info
        provider = serializer.provider
        
        # Chercher un compte social existant
        social_account = SocialAccount.objects.filter(
            provider=provider,
            provider_id=user_info['id']
        ).first()
        
        if social_account:
            # Utilisateur existant
            user = social_account.user
        else:
            # Vérifier si un utilisateur avec cet email existe
            email = user_info.get('email')
            if email:
                user = User.objects.filter(email=email).first()
                
                if user:
                    # Lier le compte social à l'utilisateur existant
                    SocialAccount.objects.create(
                        user=user,
                        provider=provider,
                        provider_id=user_info['id']
                    )
                else:
                    # Créer un nouvel utilisateur
                    username = self.generate_unique_username(user_info)
                    
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=user_info.get('given_name') or user_info.get('first_name', ''),
                        last_name=user_info.get('family_name') or user_info.get('last_name', '')
                    )
                    
                    # Créer le profil
                    user.profile = user.profile  # Créé automatiquement via signal
                    
                    # Créer le compte social
                    SocialAccount.objects.create(
                        user=user,
                        provider=provider,
                        provider_id=user_info['id']
                    )
            else:
                return Response(
                    {"error": "Email non fourni par le fournisseur d'identité"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    
    def generate_unique_username(self, user_info):
        """Génère un nom d'utilisateur unique basé sur les infos du profil social"""
        first_name = user_info.get('given_name') or user_info.get('first_name', '')
        last_name = user_info.get('family_name') or user_info.get('last_name', '')
        
        if first_name and last_name:
            base_username = f"{first_name.lower()}.{last_name.lower()}"
        else:
            # Fallback sur l'email ou un nom générique
            email = user_info.get('email', '')
            if email:
                base_username = email.split('@')[0]
            else:
                base_username = 'user'
        
        # Générer un nom d'utilisateur unique
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username

class UserPhotoViewSet(viewsets.ModelViewSet):
    """API endpoint pour la gestion des photos utilisateur"""
    serializer_class = UserPhotoSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return UserPhoto.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        try:
            photo = self.get_queryset().get(pk=pk)
            photo.is_primary = True
            photo.save()
            return Response(
                {"message": "Photo principale définie avec succès"},
                status=status.HTTP_200_OK
            )
        except UserPhoto.DoesNotExist:
            return Response(
                {"error": "Photo non trouvée"},
                status=status.HTTP_404_NOT_FOUND
            )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_verification_status(request):
    """Endpoint pour vérifier le statut de vérification d'un utilisateur"""
    user = request.user
    
    return Response({
        'is_profile_complete': user.is_complete,
        'is_phone_verified': user.is_phone_verified,
        'is_profile_verified': user.is_verified
    }, status=status.HTTP_200_OK)

def validate_google_token(access_token):
    url = f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={access_token}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    return None

def validate_facebook_token(access_token):
    url = f"https://graph.facebook.com/me?fields=id,email,first_name,last_name,picture&access_token={access_token}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    return None