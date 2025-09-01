from django.contrib import admin
from django.utils.html import format_html
from .models import User, Wallet, Transaction

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin interface for User model"""
    
    list_display = ['id', 'name', 'email', 'phone', 'wallet_balance_display', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('System Information', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def wallet_balance_display(self, obj):
        """Display wallet balance with color coding"""
        try:
            balance = obj.wallet.balance
            if balance > 100:
                color = 'green'
            elif balance > 0:
                color = 'orange'
            else:
                color = 'red'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">Rs.{}</span>',
                color,
                balance
            )
        except Wallet.DoesNotExist:
            return format_html('<span style="color: red;">No Wallet</span>')
    
    wallet_balance_display.short_description = 'Wallet Balance'
    wallet_balance_display.admin_order_field = 'wallet__balance'

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin interface for Wallet model"""
    
    list_display = ['id', 'user_name', 'balance_display', 'transaction_count', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['user__name', 'user__email']
    readonly_fields = ['id', 'updated_at', 'transaction_count_display']  #  Removed created_at
    ordering = ['-balance']
    
    fieldsets = (
        ('Wallet Information', {
            'fields': ('user', 'balance')
        }),
        ('Statistics', {
            'fields': ('transaction_count_display',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'updated_at'),  #  Removed created_at
            'classes': ('collapse',)
        }),
    )
    
    def user_name(self, obj):
        """Display user name with link"""
        return format_html(
            '<a href="/admin/wallet_api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.name
        )
    user_name.short_description = 'User'
    user_name.admin_order_field = 'user__name'
    
    def balance_display(self, obj):
        """Display balance with color coding"""
        if obj.balance > 100:
            color = 'green'
        elif obj.balance > 0:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">Rs.{}</span>',
            color,
            obj.balance
        )
    balance_display.short_description = 'Balance'
    balance_display.admin_order_field = 'balance'
    
    def transaction_count(self, obj):
        """Count of transactions for this wallet"""
        return obj.transactions.count()
    transaction_count.short_description = 'Transactions'
    
    def transaction_count_display(self, obj):
        """Display transaction count with link"""
        count = obj.transactions.count()
        return format_html(
            '<a href="/admin/wallet_api/transaction/?wallet__id={}">{} transactions</a>',
            obj.id,
            count
        )
    transaction_count_display.short_description = 'Transaction History'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin interface for Transaction model"""
    
    list_display = ['id', 'user_name', 'transaction_type_display', 'amount_display', 'description_short', 'timestamp']
    list_filter = ['transaction_type', 'timestamp', 'wallet__user']
    search_fields = ['wallet__user__name', 'wallet__user__email', 'description']
    readonly_fields = ['id', 'timestamp']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    list_per_page = 25  #  Pagination
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('wallet', 'transaction_type', 'amount', 'description')
        }),
        ('System Information', {
            'fields': ('id', 'timestamp'),
            'classes': ('collapse',)
        }),
    )
    
    def user_name(self, obj):
        """Display user name with link"""
        return format_html(
            '<a href="/admin/wallet_api/user/{}/change/">{}</a>',
            obj.wallet.user.id,
            obj.wallet.user.name
        )
    user_name.short_description = 'User'
    user_name.admin_order_field = 'wallet__user__name'
    
    def transaction_type_display(self, obj):
        """Display transaction type with color and icon"""
        if obj.transaction_type == 'CREDIT':
            color = 'green'
            icon = '⬆'  #  Changed to simpler unicode
        else:
            color = 'red'
            icon = '⬇'  #  Changed to simpler unicode
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.transaction_type
        )
    transaction_type_display.short_description = 'Type'
    transaction_type_display.admin_order_field = 'transaction_type'
    
    def amount_display(self, obj):
        """Display amount with color coding"""
        color = 'green' if obj.transaction_type == 'CREDIT' else 'red'
        symbol = '+' if obj.transaction_type == 'CREDIT' else '-'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} Rs.{}</span>',
            color,
            symbol,
            obj.amount
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def description_short(self, obj):
        """Display truncated description"""
        if len(obj.description) > 30:
            return obj.description[:30] + '...'
        return obj.description or 'No description'  #  Handle empty descriptions
    description_short.short_description = 'Description'

#  Custom Actions for bulk operations
@admin.action(description='Reset selected wallets to Rs.0')
def reset_wallet_balance(modeladmin, request, queryset):
    """Reset wallet balances to zero"""
    for wallet in queryset:
        wallet.balance = 0
        wallet.save()
    modeladmin.message_user(request, f"Reset {queryset.count()} wallet(s) to Rs.0")

# Add the action to WalletAdmin
WalletAdmin.actions = [reset_wallet_balance]

# Admin site customization
admin.site.site_header = "💰 Wallet Management System"
admin.site.site_title = "Wallet Admin"
admin.site.index_title = "Welcome to Wallet Management System"
