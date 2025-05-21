# subscriptions/services.py

import json
import uuid
import requests
import logging
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta

from subscriptions.models import Payment

logger = logging.getLogger(__name__)

class NotchPayService:
    """
    Service pour gérer les interactions avec l'API Notch Pay
    """
    
    BASE_URL = "https://api.notchpay.co"
    
    def __init__(self):
        # Récupérer les bonnes clés depuis les paramètres
        self.public_key = getattr(settings, 'NOTCHPAY_PUBLIC_KEY', '')
        self.private_key = getattr(settings, 'NOTCHPAY_PRIVATE_KEY', '')
        self.hash_key = getattr(settings, 'NOTCHPAY_HASH_KEY', '')
        
        # Log pour vérifier que les clés sont correctement récupérées
        logger.info(f"Clé publique initialisée: {self.public_key[:10]}...")
    
    def initialize_payment(self, user, amount, payment_reference, payment_type, description=None, callback_url=None):
        """
        Initialiser un paiement avec Notch Pay
        
        Args:
            user: L'utilisateur qui effectue le paiement
            amount: Le montant du paiement en FCFA
            payment_reference: Référence unique pour le paiement
            payment_type: Type de paiement (SUBSCRIPTION, EVENT, etc.)
            description: Description du paiement
            callback_url: URL de callback après paiement
            
        Returns:
            dict: Réponse de l'API contenant l'URL d'autorisation
        """
        # Construire les données du client
        customer_data = {
            'email': user.email,
            'phone': user.phone_number if user.phone_number else '',
            'name': f"{user.first_name} {user.last_name}",
            'address': {
                'country': 'CM'  # Code pays obligatoire
            }
        }
        
        # Construire la description par défaut si non fournie
        if not description:
            if payment_type == 'SUBSCRIPTION':
                description = "Abonnement Premium Findam"
            elif payment_type == 'EVENT':
                description = "Paiement pour un événement Findam"
            else:
                description = "Paiement Findam"
        
        # URL de callback par défaut
        if not callback_url:
            callback_url = f"{settings.SITE_URL}/api/subscriptions/payment-callback/"
        
        # Construire le payload pour l'API
        payload = {
            "currency": "XAF",
            "amount": amount,
            "reference": payment_reference,
            "customer": customer_data,
            "description": description,
            "callback": callback_url,
            "locked_currency": "XAF",
            "locked_country": "CM"
        }
        
        logger.info(f"Payload pour Notch Pay: {payload}")
        
        # Faire la requête à l'API avec la clé publique
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self.public_key  # Utilisez la clé publique dans l'en-tête
        }
        
        try:
            logger.info(f"Envoi de la requête à {self.BASE_URL}/payments avec clé publique: {self.public_key[:10]}...")
            response = requests.post(
                f"{self.BASE_URL}/payments",
                json=payload,
                headers=headers
            )
            
            logger.info(f"Statut de la réponse: {response.status_code}")
            logger.info(f"Contenu de la réponse: {response.text}")
            
            if response.status_code == 201:
                return response.json()
            else:
                try:
                    error_data = response.json() if response.content else {"error": "Erreur inconnue"}
                except:
                    error_data = {"error": "Erreur de parsing de la réponse", "text": response.text}
                
                logger.error(f"Erreur lors de l'initialisation du paiement: {error_data}")
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "data": error_data,
                    "message": error_data.get("message", "Erreur inconnue")
                }
        
        except Exception as e:
            logger.exception(f"Exception lors de l'appel à l'API Notch Pay: {str(e)}")
            return {
                "error": True,
                "message": str(e)
            }
    
    def verify_payment(self, payment_reference):
        """
        Vérifier le statut d'un paiement
        
        Args:
            payment_reference: Référence du paiement à vérifier
            
        Returns:
            dict: Détails du paiement
        """
        try:
            # S'assurer que la référence est bien une référence NotchPay
            # Les références NotchPay commencent généralement par 'trx.'
            if not payment_reference.startswith('trx.') and Payment.objects.filter(reference=payment_reference).exists():
                # Si c'est une référence interne, essayer de récupérer la référence NotchPay
                payment = Payment.objects.get(reference=payment_reference)
                if payment.notchpay_reference:
                    payment_reference = payment.notchpay_reference
                    logger.info(f"Référence convertie: {payment_reference} -> {payment.notchpay_reference}")
            
            logger.info(f"Vérification du paiement avec référence: {payment_reference}")
            
            response = requests.get(
                f"{self.BASE_URL}/payments/{payment_reference}",
                headers={
                    "Accept": "application/json",
                    "Authorization": self.public_key
                }
            )
            
            logger.info(f"Vérification du paiement - Status: {response.status_code}")
            logger.info(f"Vérification du paiement - Contenu: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    error_data = response.json() if response.content else {"error": "Erreur inconnue"}
                except:
                    error_data = {"error": "Erreur de parsing de la réponse", "text": response.text}
                
                logger.error(f"Erreur lors de la vérification du paiement: {error_data}")
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "data": error_data,
                    "message": error_data.get("message", "Erreur inconnue")
                }
        
        except Exception as e:
            logger.exception(f"Exception lors de la vérification du paiement: {str(e)}")
            return {
                "error": True,
                "message": str(e)
            }
    
    def process_mobile_payment(self, payment_reference, phone_number, channel="cm.mobile"):
        """
        Traiter un paiement Mobile Money
        
        Args:
            payment_reference: Référence du paiement
            phone_number: Numéro de téléphone à débiter
            channel: Canal de paiement (cm.mobile, cm.mtn, cm.orange)
            
        Returns:
            dict: Résultat du traitement
        """
        # Assurez-vous que le numéro de téléphone est au format international
        if phone_number and not phone_number.startswith('+237'):
            phone_number = '+237' + phone_number
        
        # Mapper correctement les canaux de paiement
        channel_mapping = {
            'CM_MOBILE': 'cm.mobile',
            'CM_MTN': 'cm.mtn',
            'CM_ORANGE': 'cm.orange'
        }
        
        # Utiliser le mappage si nécessaire
        if channel in channel_mapping:
            channel = channel_mapping[channel]
            
        logger.info(f"Traitement du paiement mobile pour {payment_reference} via {channel} au numéro {phone_number}")
        
        payload = {
            "channel": channel,
            "phone": phone_number
        }
        
        # Log du payload pour débogage
        logger.info(f"Payload du paiement mobile: {payload}")
        
        try:
            # Vérifier d'abord si le paiement existe
            verify_response = requests.get(
                f"{self.BASE_URL}/payments/{payment_reference}",
                headers={
                    "Accept": "application/json",
                    "Authorization": self.public_key
                }
            )
            
            # Log de la vérification
            logger.info(f"Vérification du paiement - Status: {verify_response.status_code}")
            if verify_response.status_code != 200:
                logger.error(f"Le paiement {payment_reference} n'existe pas ou n'est pas accessible")
                return {
                    "error": True,
                    "status_code": verify_response.status_code,
                    "message": "Paiement non trouvé ou inaccessible"
                }
            
            # Si le paiement existe, procéder au traitement mobile
            response = requests.post(
                f"{self.BASE_URL}/payments/{payment_reference}",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": self.public_key
                }
            )
            
            logger.info(f"Réponse du paiement mobile - Status: {response.status_code}, Contenu: {response.text}")
            
            if response.status_code == 202:
                return response.json()
            else:
                try:
                    error_data = response.json() if response.content else {"error": "Erreur inconnue"}
                except:
                    error_data = {"error": "Erreur de parsing de la réponse", "text": response.text}
                
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "data": error_data,
                    "message": error_data.get("message", "Erreur inconnue")
                }
        
        except Exception as e:
            logger.exception(f"Exception lors du traitement du paiement mobile: {str(e)}")
            return {
                "error": True,
                "message": str(e)
            }
            
    def cancel_payment(self, payment_reference):
        """
        Annuler un paiement
        
        Args:
            payment_reference: Référence du paiement à annuler
            
        Returns:
            dict: Résultat de l'annulation
        """
        try:
            response = requests.delete(
                f"{self.BASE_URL}/payments/{payment_reference}",
                headers={
                    "Accept": "application/json",
                    "Authorization": self.public_key  # Utilisez la clé publique
                }
            )
            
            logger.info(f"Annulation du paiement - Status: {response.status_code}, Contenu: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    error_data = response.json() if response.content else {"error": "Erreur inconnue"}
                except:
                    error_data = {"error": "Erreur de parsing de la réponse", "text": response.text}
                
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "data": error_data
                }
        
        except Exception as e:
            logger.exception(f"Exception lors de l'annulation du paiement: {str(e)}")
            return {
                "error": True,
                "message": str(e)
            }
    
    @staticmethod
    def generate_payment_reference():
        """
        Générer une référence unique pour un paiement
        
        Returns:
            str: Référence de paiement unique
        """
        return f"findam-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:8]}"