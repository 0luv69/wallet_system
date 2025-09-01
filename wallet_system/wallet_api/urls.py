from django.urls import path
from .views import UserListView, UpdateWalletView, UserTransactionsView, APIKeyManagementView

# URL patterns for wallet API endpoints
urlpatterns = [
    # API Key Management
    path('api-keys/create/', APIKeyManagementView.as_view(), name='create-api-key'),

    # User Management URLs
    path('users/', UserListView.as_view(), name='user-list'),
    
    # Wallet Management URLs  
    path('wallets/<int:user_id>/update/', UpdateWalletView.as_view(), name='update-wallet'),
    
    # Transaction Management URLs
    path('transactions/<int:user_id>/', UserTransactionsView.as_view(), name='user-transactions'),
]