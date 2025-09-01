from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import APIKey

class APIKeyAuthentication(BaseAuthentication):
    """API Key Authentication with database lookup"""
    
    def authenticate(self, request):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return None  # No authentication provided
        
        try:
            # Database lookup - approach
            api_key_obj = APIKey.objects.select_related('user').get(
                key=api_key,
                is_active=True
            )
            
            # Check expiration
            if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
                raise AuthenticationFailed('API Key expired')
            
            # Update last used timestamp
            api_key_obj.last_used = timezone.now()
            api_key_obj.save(update_fields=['last_used'])
            
            return (api_key_obj.user, api_key_obj)
            
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid API Key')
    
    def authenticate_header(self, request):
        return 'X-API-Key'