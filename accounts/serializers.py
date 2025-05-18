# accounts/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta
import random
import string

from .models import UserProfile, UserPhoto, VerificationCode, SocialAccount

User = get_user_model()

class UserPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPhoto
        fields = ('id', 'image', 'is_primary', 'uploaded_at')
        read_only_fields = ('uploaded_at',)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('height', 'education', 'job_title', 'company', 
                 'relationship_status', 'has_children', 'interests', 
                 'about_me', 'looking_for')

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    photos = UserPhotoSerializer(many=True, read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'first_name', 
                 'last_name', 'date_of_birth', 'gender', 'seeking', 'bio', 
                 'location', 'latitude', 'longitude', 'is_premium', 
                 'premium_until', 'is_verified', 'is_complete', 'age',
                 'profile', 'photos', 'last_active')
        read_only_fields = ('id', 'is_premium', 'premium_until', 'is_verified', 
                           'last_active')
    
    def get_age(self, obj):
        return obj.get_age()
    
    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        user = User.objects.create_user(**validated_data)
        if profile_data:
            UserProfile.objects.create(user=user, **profile_data)
        else:
            UserProfile.objects.create(user=user)
        return user
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Mise à jour des champs utilisateur
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Mise à jour du profil
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        # Vérifier si le profil est complet
        self._check_profile_completeness(instance)
        
        return instance
    
    def _check_profile_completeness(self, user):
        """Vérifie si le profil est complet"""
        is_complete = (
            user.username and 
            user.email and 
            user.first_name and 
            user.last_name and 
            user.date_of_birth and 
            user.gender and 
            user.seeking and 
            user.bio and 
            user.location and 
            user.latitude is not None and 
            user.longitude is not None and 
            hasattr(user, 'profile') and
            user.photos.filter(is_primary=True).exists()
        )
        
        if is_complete != user.is_complete:
            user.is_complete = is_complete
            user.save(update_fields=['is_complete'])

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        return user

class PhoneVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    
    def validate_phone_number(self, value):
        from django.core.validators import RegexValidator
        phone_regex = RegexValidator(
            regex=r'^\+?237?\d{9}$',
            message="Le numéro doit être au format: '+237xxxxxxxxx'. 9 chiffres maximum."
        )
        phone_regex(value)
        
        # Vérifier si le numéro existe déjà
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        
        return value
    
    def create_verification_code(self, user):
        # Générer un code à 6 chiffres
        code = ''.join(random.choices(string.digits, k=6))
        
        # Créer l'entrée de vérification
        VerificationCode.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        return code

class VerifyPhoneCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    code = serializers.CharField(required=True)
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        code = attrs.get('code')
        
        user = User.objects.filter(phone_number=phone_number).first()
        if not user:
            raise serializers.ValidationError({"phone_number": "Utilisateur non trouvé."})
        
        verification = VerificationCode.objects.filter(
            user=user,
            code=code,
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if not verification:
            raise serializers.ValidationError({"code": "Code invalide ou expiré."})
        
        # Stocker pour utilisation dans la vue
        self.user = user
        self.verification = verification
        
        return attrs

class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=SocialAccount.PROVIDER_CHOICES)
    access_token = serializers.CharField()
    
    def validate(self, attrs):
        provider = attrs.get('provider')
        access_token = attrs.get('access_token')
        
        # Vérifier le token avec le fournisseur d'identité
        if provider == 'google':
            user_info = self.validate_google_token(access_token)
        elif provider == 'facebook':
            user_info = self.validate_facebook_token(access_token)
        else:
            raise serializers.ValidationError({"provider": "Fournisseur non supporté."})
        
        if not user_info:
            raise serializers.ValidationError({"access_token": "Token invalide."})
        
        # Stocker les informations pour la vue
        self.user_info = user_info
        self.provider = provider
        
        return attrs
    
    def validate_google_token(self, access_token):
        """Validation du token Google avec les API Google"""
        # Dans une implémentation réelle, cette méthode ferait une requête à l'API Google
        # Pour simplifier, nous simulons une réponse valide
        
        # Simulation d'une validation réussie
        return {
            'id': '123456789',
            'email': 'user@example.com',
            'given_name': 'Prénom',
            'family_name': 'Nom',
            'picture': 'https://example.com/picture.jpg'
        }
    
    def validate_facebook_token(self, access_token):
        """Validation du token Facebook avec les API Facebook"""
        # Dans une implémentation réelle, cette méthode ferait une requête à l'API Facebook
        # Pour simplifier, nous simulons une réponse valide
        
        # Simulation d'une validation réussie
        return {
            'id': '987654321',
            'email': 'user@example.com',
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'picture': {'data': {'url': 'https://example.com/picture.jpg'}}
        }

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Les nouveaux mots de passe ne correspondent pas."})
        return attrs