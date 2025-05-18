# subscriptions/services.py

import json
import uuid
import requests
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta

class NotchPayService:
    """
    Service pour gérer les interactions avec l'API Notch Pay
    """
    
    BASE_URL = "https://api.notchpay.co"
    
    def __init__(self):
        self.api_key = getattr(settings, 'NOTCHPAY_API_KEY', 'votre_cle_api_par_defaut')
    
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
        
        # Faire la requête à l'API
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/payments",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                error_data = response.json() if response.content else {"error": "Erreur inconnue"}
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "data": error_data
                }
        
        except Exception as e:
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
            response = requests.get(
                f"{self.BASE_URL}/payments/{payment_reference}",
                headers={
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json() if response.content else {"error": "Erreur inconnue"}
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "data": error_data
                }
        
        except Exception as e:
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
        payload = {
            "channel": channel,
            "phone": phone_number
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/payments/{payment_reference}",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 202:
                return response.json()
            else:
                error_data = response.json() if response.content else {"error": "Erreur inconnue"}
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "data": error_data
                }
        
        except Exception as e:
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
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json() if response.content else {"error": "Erreur inconnue"}
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "data": error_data
                }
        
        except Exception as e:
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