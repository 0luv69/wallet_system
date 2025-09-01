from django.db import models
from django.core.validators import RegexValidator
from decimal import Decimal
import secrets
from django.contrib.auth.models import User as AuthUser
from django.utils import timezone

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?977?\d{9,11}$',
        message="Phone number must be entered in the format: '+9779999999999'. Up to 10 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def save(self, *args, **kwargs):
        # Create wallet automatically when user is created
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Wallet.objects.get_or_create(user=self)

    class Meta:
        ordering = ['name']

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.name}'s Wallet - Balance: Rs.{self.balance}"
    
    def add_funds(self,  amount, description=""):
        """Add funds to wallet and create transaction record"""
        self.balance += Decimal(str(amount))
        self.save()

                # Create transaction record
        Transaction.objects.create(
            wallet=self,
            amount=Decimal(str(amount)),
            transaction_type='CREDIT',
            description=description or f"Added Rs.{amount} to wallet"
        )
        
    def deduct_funds(self, amount,  description=""):
        """Deduct funds from wallet and create transaction record"""
        amount_decimal = Decimal(str(amount))
        if self.balance >= amount_decimal:
            self.balance -= amount_decimal
            self.save()

            # Create transaction record
            Transaction.objects.create(
                wallet=self,
                amount=amount_decimal,
                transaction_type='DEBIT',
                description=description or f"Deducted Rs.{amount} from wallet"
            )
            return True

        return False

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type} Rs.{self.amount} - {self.wallet.user.name}"
    
    class Meta:
        ordering = ['-timestamp']






class APIKey(models.Model):
    """ API Key management"""
    
    name = models.CharField(max_length=100, help_text="API key name/description")
    key = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE, related_name='api_keys')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
    
    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_key():
        """Generate secure API key"""
        return f"wlt_{secrets.token_urlsafe(32)}"
    
    def set_expiration(self, days=30):
        """Set expiration date for the API key"""
        self.expires_at = timezone.now() + timezone.timedelta(days=days)
        self.save(update_fields=['expires_at'])
    
    def __str__(self):
        return f"{self.name} - {self.key[:8]}..."