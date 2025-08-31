from django.urls import path
from .views import UserListView, UpdateWalletView, UserTransactionsView

# URL patterns for wallet API endpoints
urlpatterns = [
    # User Management URLs
    path('users/', UserListView.as_view(), name='user-list'),
    
    # Wallet Management URLs  
    path('wallets/<int:user_id>/update/', UpdateWalletView.as_view(), name='update-wallet'),
    
    # Transaction Management URLs
    path('transactions/<int:user_id>/', UserTransactionsView.as_view(), name='user-transactions'),
]