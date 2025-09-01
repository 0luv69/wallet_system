import time
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from wallet_api.models import APIKey
from django.utils import timezone

class RateLimitMiddleware:
    """rate limiting middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.limits = getattr(settings, 'RATE_LIMITS', {
            'default': {'requests': 100, 'window': 3600},  # 100 per hour
            'wallet_update': {'requests': 10, 'window': 300}  # 10 per 5 min for sensitive ops
        })

    def __call__(self, request):
        if request.path.startswith('/api/'):
            # Determine limit based on endpoint
            limit_key = 'default'
            if 'wallets' in request.path and request.method in ['PUT', 'POST']:
                limit_key = 'wallet_update'
            
            if not self.check_rate_limit(request, limit_key):
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {self.limits[limit_key]["requests"]} per {self.limits[limit_key]["window"]} seconds',
                    'retry_after': self.limits[limit_key]['window']
                }, status=429)
        
        return self.get_response(request)
    
    def check_rate_limit(self, request, limit_key):
        """Check if request is within rate limit"""
        client_id = self.get_client_identifier(request)
        cache_key = f'rate_limit_{limit_key}_{client_id}'
        
        limit_config = self.limits[limit_key]
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit_config['requests']:
            return False
        
        cache.set(cache_key, current_count + 1, limit_config['window'])
        return True
    
    def get_client_identifier(self, request):
        """Get client identifier (IP + API key if available)"""
        api_key = request.headers.get('X-API-Key', 'anonymous')
        client_ip = self.get_client_ip(request)
        return f"{client_ip}_{api_key[:8]}"
    
    def get_client_ip(self, request):
        """Get real client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    