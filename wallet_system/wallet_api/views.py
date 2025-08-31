from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import User, Wallet, Transaction
from .serializers import (
    UserSerializer, 
    UserCreateSerializer,
    TransactionSerializer, 
    UpdateWalletSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class UserListView(APIView):
    """
    API View for listing all users with their wallet balances
    GET /api/users/ - List all users
    POST /api/users/ - Create new user
    """
    
    @swagger_auto_schema(
        operation_summary="List all users with wallet balances",
        operation_description="Requirement 1: Fetch all users details (name, email, phone) along with their wallet balance",
        responses={
            200: openapi.Response(
                description="List of users with wallet balances",
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "name": "Luv King",
                            "email": "luv@king.com",
                            "phone": "+9770000000",
                            "wallet_balance": "150.50",
                            "created_at": "2025-08-31T15:38:10Z"
                        }
                    ]
                }
            )
        }
    )
    def get(self, request):
        """List Users API – Fetch all users details (name, email, phone) along with their wallet balance"""
        
        # Optimize query to avoid N+1 problem
        users = User.objects.all().select_related('wallet').order_by('name')
        
        # Serialize the data
        serializer = UserSerializer(users, many=True)
        
        return Response({
            "message": "Users retrieved successfully",
            "count": len(serializer.data),
            "users": serializer.data
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_summary="Create a new user",
        operation_description="Create a new user with automatic wallet creation",
        request_body=UserCreateSerializer,
        responses={
            201: UserSerializer,
            400: "Validation errors"
        }
    )
    def post(self, request):
        """Create new user (wallet will be auto-created via model save method)"""
        
        # Validate input data
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "error": "Invalid data provided",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user (wallet auto-created in model save method)
        user = serializer.save()
        
        # Return full user data with wallet balance
        response_serializer = UserSerializer(user)
        
        return Response({
            "message": "User created successfully",
            "user": response_serializer.data
        }, status=status.HTTP_201_CREATED)

class UpdateWalletView(APIView):
    """
    API View for updating wallet balance
    PUT /api/wallets/{user_id}/update/
    """
    
    @swagger_auto_schema(
        operation_summary="Update user's wallet balance",
        operation_description="Requirement 2: Add or update an amount in any particular user's wallet",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_PATH,
                description="ID of the user whose wallet to update",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        request_body=UpdateWalletSerializer,
        responses={
            200: openapi.Response(
                description="Wallet updated successfully",
                examples={
                    "application/json": {
                        "message": "Wallet updated successfully",
                        "user": "John Doe",
                        "transaction_type": "CREDIT",
                        "amount": "100.00",
                        "previous_balance": "150.50",
                        "new_balance": "250.50",
                        "transaction_id": 123
                    }
                }
            ),
            400: "Bad Request - Validation errors or insufficient funds",
            404: "User not found"
        }
    )
    def put(self, request, user_id):
        """Update Wallet API – Add or update an amount in any particular user's wallet"""
        
        # Get user or return 404
        user = get_object_or_404(User, id=user_id)
        
        # Validate request data
        serializer = UpdateWalletSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "error": "Invalid request data",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        validated_data = serializer.validated_data
        amount = validated_data['amount']
        transaction_type = validated_data['transaction_type']
        description = validated_data.get('description', '')
        
        # Store previous balance for response
        previous_balance = user.wallet.balance
        
        # Use database transaction for data consistency
        try:
            with transaction.atomic():
                wallet = user.wallet
                
                if transaction_type == 'CREDIT':
                    # Add money to wallet
                    wallet.add_funds(amount, description or f"Added ${amount} to wallet")
                    action_message = f"Added ${amount} to {user.name}'s wallet"
                    
                elif transaction_type == 'DEBIT':
                    # Check if sufficient funds and deduct
                    if wallet.balance < amount:
                        return Response({
                            "error": "Insufficient funds",
                            "current_balance": str(wallet.balance),
                            "requested_amount": str(amount),
                            "shortfall": str(amount - wallet.balance)
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    wallet.deduct_funds(amount, description or f"Deducted ${amount} from wallet")
                    action_message = f"Deducted ${amount} from {user.name}'s wallet"
                
                # Refresh to get updated balance
                wallet.refresh_from_db()
                
                # Get the latest transaction for reference
                latest_transaction = Transaction.objects.filter(wallet=wallet).first()
                
                return Response({
                    "message": action_message,
                    "user": user.name,
                    "user_id": user.id,
                    "user_email": user.email,
                    "transaction_type": transaction_type,
                    "amount": str(amount),
                    "previous_balance": str(previous_balance),
                    "new_balance": str(wallet.balance),
                    "description": description,
                    "transaction_id": latest_transaction.id if latest_transaction else None,
                    "timestamp": wallet.updated_at.isoformat()
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({
                "error": "Failed to update wallet",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserTransactionsView(APIView):
    """
    API View for fetching user's transaction history
    GET /api/transactions/{user_id}/
    """
    
    @swagger_auto_schema(
        operation_summary="Get user's transaction history",
        operation_description="Requirement 3: Fetch all wallet transactions for a specific user by passing their user_id",
        manual_parameters=[
            openapi.Parameter(
                'user_id',
                openapi.IN_PATH,
                description="ID of the user whose transactions to fetch",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'transaction_type',
                openapi.IN_QUERY,
                description="Filter by transaction type (CREDIT or DEBIT)",
                type=openapi.TYPE_STRING,
                required=False,
                enum=['CREDIT', 'DEBIT']
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Number of recent transactions to return (default: 50)",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="User transaction history",
                examples={
                    "application/json": {
                        "message": "Transactions retrieved successfully",
                        "user": {
                            "id": 1,
                            "name": "John Doe",
                            "email": "john@example.com",
                            "current_balance": "250.50"
                        },
                        "summary": {
                            "total_transactions": 10,
                            "filtered_count": 5,
                            "total_credits": "500.00",
                            "total_debits": "249.50"
                        },
                        "transactions": []
                    }
                }
            ),
            404: "User not found"
        }
    )
    def get(self, request, user_id):
        """Fetch Transactions API – Fetch all wallet transactions for a specific user by user_id"""
        
        # Get user or return 404
        user = get_object_or_404(User, id=user_id)
        
        # Get query parameters for filtering
        transaction_type = request.query_params.get('transaction_type', '').upper()
        limit = request.query_params.get('limit', '50')
        
        # Validate limit parameter
        try:
            limit = int(limit)
            if limit <= 0:
                limit = 50
        except ValueError:
            limit = 50
        
        # Get base query for user's transactions
        transactions_query = Transaction.objects.filter(
            wallet=user.wallet
        ).order_by('-timestamp')
        
        # Apply transaction type filter if provided
        if transaction_type and transaction_type in ['CREDIT', 'DEBIT']:
            filtered_transactions = transactions_query.filter(transaction_type=transaction_type)
        else:
            filtered_transactions = transactions_query
        
        # Apply limit
        transactions = filtered_transactions[:limit]
        
        # Calculate summary statistics
        all_transactions = transactions_query
        total_credits = sum([t.amount for t in all_transactions.filter(transaction_type='CREDIT')])
        total_debits = sum([t.amount for t in all_transactions.filter(transaction_type='DEBIT')])
        
        # Serialize transaction data
        serializer = TransactionSerializer(transactions, many=True)
        
        return Response({
            "message": "Transactions retrieved successfully",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "current_balance": str(user.wallet.balance)
            },
            "summary": {
                "total_transactions": all_transactions.count(),
                "filtered_count": len(serializer.data),
                "total_credits": str(total_credits),
                "total_debits": str(total_debits),
                "net_balance": str(total_credits - total_debits)
            },
            "filters_applied": {
                "transaction_type": transaction_type if transaction_type else "ALL",
                "limit": limit
            },
            "transactions": serializer.data
        }, status=status.HTTP_200_OK)