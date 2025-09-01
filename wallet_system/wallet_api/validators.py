from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from django.conf import settings

class WalletValidators:
    """ wallet validation class"""
    
    @staticmethod
    def validate_amount(value):
        """ amount validation with configurable limits"""
        min_amount = getattr(settings, 'MIN_TRANSACTION_AMOUNT', Decimal('0.01'))
        max_amount = getattr(settings, 'MAX_TRANSACTION_AMOUNT', Decimal('10000.00'))
        
        if value < min_amount:
            raise serializers.ValidationError(f"Amount must be at least ${min_amount}")
        
        if value > max_amount:
            raise serializers.ValidationError(f"Amount exceeds maximum limit of ${max_amount}")
        
        # Validate decimal places
        if value.as_tuple().exponent < -2:
            raise serializers.ValidationError("Amount can have maximum 2 decimal places")
        
        return value