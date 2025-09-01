from rest_framework import serializers
from .models import User, Wallet, Transaction
from decimal import Decimal
from .validators import WalletValidators

class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model - shows wallet balance info"""
    
    class Meta:
        model = Wallet
        fields = ['balance', 'updated_at']
        read_only_fields = ['balance', 'updated_at']  # These can't be directly modified

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - includes wallet balance"""
    
    wallet_balance = serializers.SerializerMethodField()  # Custom field
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'wallet_balance', 'created_at']
        read_only_fields = ['id', 'created_at', 'wallet_balance']
    
    def get_wallet_balance(self, obj):
        """Custom method to get wallet balance"""
        try:
            return str(obj.wallet.balance)  # Convert Decimal to string for JSON
        except Wallet.DoesNotExist:
            return "0.00"  # Default if no wallet exists

class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model - shows transaction history"""
    
    user_name = serializers.CharField(source='wallet.user.name', read_only=True)
    user_email = serializers.CharField(source='wallet.user.email', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 
            'amount', 
            'transaction_type', 
            'description', 
            'timestamp',
            'user_name',
            'user_email'
        ]
        read_only_fields = ['id', 'timestamp', 'user_name', 'user_email']

class UpdateWalletSerializer(serializers.Serializer):
    """Custom serializer for updating wallet balance"""
    
    amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[WalletValidators.validate_amount],
        help_text="Amount to add or deduct from wallet"
    )
    transaction_type = serializers.ChoiceField(
        choices=Transaction.TRANSACTION_TYPES,
        help_text="CREDIT to add money, DEBIT to deduct money"
    )
    description = serializers.CharField(
        max_length=500, 
        required=False, 
        allow_blank=True,
        help_text="Optional description for the transaction"
    )
    
    def validate_amount(self, value):
        """Custom validation for amount field"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        if value > Decimal('999999.99'):
            raise serializers.ValidationError("Amount cannot exceed 999,999.99")
        return value
    
    def validate(self, data):
        """Custom validation for the entire serializer"""
        # You can add more complex validation here if needed
        # For example, checking business rules
        return data

class UserCreateSerializer(serializers.ModelSerializer):
    """Separate serializer for creating users"""
    
    class Meta:
        model = User
        fields = ['name', 'email', 'phone']
    
    def validate_email(self, value):
        """Custom validation for email"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value