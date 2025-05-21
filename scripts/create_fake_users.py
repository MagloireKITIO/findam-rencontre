# scripts/create_fake_users.py

import os
import django
import random
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.images import ImageFile
from faker import Faker
import requests
from io import BytesIO
import sys

# Configurer l'environnement Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'findam.settings')
django.setup()

from accounts.models import UserProfile, UserPhoto
from matchmaking.models import UserPreference

# Initialiser Faker
fake = Faker(['fr_FR'])
User = get_user_model()

# Paramètres configurables
NUM_USERS = 30  # Nombre d'utilisateurs à créer
LOCATIONS = [
    {'name': 'Douala', 'lat': 4.0511, 'lng': 9.7679},
    {'name': 'Yaoundé', 'lat': 3.8480, 'lng': 11.5021},
    {'name': 'Bafoussam', 'lat': 5.4764, 'lng': 10.4146},
    {'name': 'Garoua', 'lat': 9.3019, 'lng': 13.3921},
    {'name': 'Limbé', 'lat': 4.0225, 'lng': 9.2000},
    {'name': 'Ngaoundéré', 'lat': 7.3267, 'lng': 13.5833},
    {'name': 'Bertoua', 'lat': 4.5785, 'lng': 13.6846},
    {'name': 'Maroua', 'lat': 10.5957, 'lng': 14.3238},
    {'name': 'Bamenda', 'lat': 5.9631, 'lng': 10.1591},
    {'name': 'Ebolowa', 'lat': 2.9000, 'lng': 11.1500},
]

# Fonction pour télécharger des photos de profil depuis une API
def download_profile_picture(gender):
    """Télécharge une photo de profil depuis une API d'avatars"""
    gender_param = "male" if gender == 'M' else "female"
    try:
        response = requests.get(f'https://randomuser.me/api/?gender={gender_param}&nat=fr')
        data = response.json()
        image_url = data['results'][0]['picture']['large']
        image_response = requests.get(image_url)
        return BytesIO(image_response.content)
    except Exception as e:
        print(f"Erreur lors du téléchargement de l'image: {e}")
        return None

def create_fake_users():
    """Crée des utilisateurs fictifs avec des profils complets"""
    print(f"Création de {NUM_USERS} utilisateurs fictifs...")
    
    created_count = 0
    for i in range(NUM_USERS):
        # Déterminer le genre de l'utilisateur
        gender = random.choice(['M', 'F'])
        seeking = random.choice(['M', 'F', 'B'])
        
        # Générer un nom d'utilisateur unique
        username = fake.user_name() + str(random.randint(100, 999))
        
        # Vérifier si l'utilisateur existe déjà
        if User.objects.filter(username=username).exists():
            continue
            
        # Date de naissance (18-60 ans)
        dob = fake.date_of_birth(minimum_age=18, maximum_age=60)
        
        # Créer le dictionnaire de données utilisateur
        user_data = {
            'username': username,
            'email': fake.email(),
            'password': 'Password123!',  # Mot de passe par défaut
            'first_name': fake.first_name_male() if gender == 'M' else fake.first_name_female(),
            'last_name': fake.last_name(),
            'date_of_birth': dob,
            'gender': gender,
            'seeking': seeking,
            'bio': fake.paragraph(nb_sentences=5),
            'is_active': True,
            'is_verified': random.random() > 0.3,  # 70% des utilisateurs sont vérifiés
            'phone_number': '+237' + ''.join([str(random.randint(0, 9)) for _ in range(9)]),
            'is_phone_verified': random.random() > 0.2,  # 80% ont vérifié leur téléphone
            'is_premium': random.random() > 0.7,  # 30% sont premium
        }
        
        # Ajouter une localisation aléatoire
        location = random.choice(LOCATIONS)
        user_data['location'] = location['name']
        user_data['latitude'] = location['lat'] + random.uniform(-0.05, 0.05)
        user_data['longitude'] = location['lng'] + random.uniform(-0.05, 0.05)
        
        # Ajouter une date premium si l'utilisateur est premium
        if user_data['is_premium']:
            premium_days = random.randint(1, 180)
            user_data['premium_until'] = datetime.now() + timedelta(days=premium_days)
        
        try:
            # Créer l'utilisateur
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password']
            )
            
            # Mettre à jour les champs additionnels
            for key, value in user_data.items():
                if key not in ['username', 'email', 'password'] and hasattr(user, key):
                    setattr(user, key, value)
            
            user.save()
            
            # Mettre à jour le profil
            profile_data = {
                'height': random.randint(150, 200),
                'education': random.choice(['HS', 'UG', 'GD', 'PD', 'OT']),
                'job_title': fake.job(),
                'company': fake.company(),
                'relationship_status': random.choice(['S', 'R', 'E', 'M', 'D', 'W', 'C']),
                'has_children': random.random() > 0.7,
                'interests': ', '.join([fake.word() for _ in range(random.randint(3, 8))]),
                'about_me': fake.paragraph(nb_sentences=3),
                'looking_for': fake.paragraph(nb_sentences=2),
            }
            
            # Mettre à jour le profil utilisateur
            profile = user.profile
            for key, value in profile_data.items():
                setattr(profile, key, value)
            profile.save()
            
            # Créer les préférences utilisateur
            preferences_data = {
                'min_age': random.randint(18, 40),
                'max_age': random.randint(25, 60),
                'distance': random.choice([10, 20, 30, 50, 100]),
                'show_verified_only': random.random() > 0.5,
            }
            
            # S'assurer que min_age < max_age
            if preferences_data['min_age'] >= preferences_data['max_age']:
                preferences_data['max_age'] = preferences_data['min_age'] + random.randint(5, 20)
            
            # Créer ou mettre à jour les préférences
            preferences, _ = UserPreference.objects.get_or_create(user=user)
            for key, value in preferences_data.items():
                setattr(preferences, key, value)
            preferences.save()
            
            # Télécharger et enregistrer des photos de profil
            num_photos = random.randint(1, 4)
            for j in range(num_photos):
                image_io = download_profile_picture(gender)
                if image_io:
                    try:
                        photo = UserPhoto(user=user, is_primary=(j == 0))
                        filename = f"{user.username}_{j}.jpg"
                        photo.image.save(filename, ImageFile(image_io))
                        photo.save()
                    except Exception as e:
                        print(f"Erreur lors de l'enregistrement de la photo: {e}")
            
            # Marquer comme complet si toutes les conditions sont remplies
            if user.photos.filter(is_primary=True).exists():
                user.is_complete = True
                user.save()
            
            created_count += 1
            print(f"Créé {created_count}/{NUM_USERS}: {user.username} ({user.gender})")
            
        except Exception as e:
            print(f"Erreur lors de la création de l'utilisateur {i+1}: {e}")
    
    print(f"Terminé! {created_count} utilisateurs fictifs créés.")

if __name__ == "__main__":
    create_fake_users()