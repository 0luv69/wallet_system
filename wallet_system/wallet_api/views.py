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

from .models import APIKey
from .authentication import APIKeyAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User as AuthUser

# RESPONSE SCHEMAS
api_key_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
        "api_key": openapi.Schema(type=openapi.TYPE_STRING),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "user_id": openapi.Schema(type=openapi.TYPE_STRING),
        "expires_at": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
    }
)
simple_error_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "error": openapi.Schema(type=openapi.TYPE_STRING),
        "details": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
    }
)
auth_error_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "detail": openapi.Schema(type=openapi.TYPE_STRING)
    }
)
rate_limit_error_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "error": openapi.Schema(type=openapi.TYPE_STRING),
        "message": openapi.Schema(type=openapi.TYPE_STRING)
    }
)

user_list_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
        "count": openapi.Schema(type=openapi.TYPE_INTEGER),
        "users": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT))
    }
)
user_create_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
        "user": openapi.Schema(type=openapi.TYPE_OBJECT)
    }
)
wallet_update_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
        "user": openapi.Schema(type=openapi.TYPE_STRING),
        "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "user_email": openapi.Schema(type=openapi.TYPE_STRING),
        "transaction_type": openapi.Schema(type=openapi.TYPE_STRING),
        "amount": openapi.Schema(type=openapi.TYPE_STRING),
        "previous_balance": openapi.Schema(type=openapi.TYPE_STRING),
        "new_balance": openapi.Schema(type=openapi.TYPE_STRING),
        "description": openapi.Schema(type=openapi.TYPE_STRING),
        "transaction_id": openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
        "timestamp": openapi.Schema(type=openapi.TYPE_STRING),
    }
)
transactions_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
        "user": openapi.Schema(type=openapi.TYPE_OBJECT),
        "summary": openapi.Schema(type=openapi.TYPE_OBJECT),
        "filters_applied": openapi.Schema(type=openapi.TYPE_OBJECT),
        "transactions": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
    }
)

# Api View
class APIKeyManagementView(APIView):
    """API Key management endpoint"""

    @swagger_auto_schema(
        tags=['🔑 API Key Management'],
        operation_summary="Create new API key",
        operation_description="Generate a new API key for accessing wallet APIs",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='API key name, to call api key, optional'),
                'user_id': openapi.Schema(type=openapi.TYPE_STRING, description='User ID for API key')
            },
            required=['user_id']
        ),
        responses={
            201: openapi.Response(
                description="API Key created successfully",
                schema=api_key_response_schema,
                example={
                    "message": "API Key created successfully",
                    "api_key": "wlt_xB9kF2mP4nQ8rL5vW3cT7jK1dH6sA9eR",
                    "name": "Test Key",
                    "user_id": "1",
                    "expires_at": None,
                    "created_at": "2025-09-01T01:55:00Z"
                }
            ),
            400: openapi.Response(
                description="Invalid request",
                schema=simple_error_schema,
                example={
                    "error": "The 'user_id' is required"
                }
            ),
            404: openapi.Response(
                description="User not found",
                schema=simple_error_schema,
                example={
                    "error": "User with ID '1' does not exist"
                }
            ),
            500: openapi.Response(
                description="Internal error",
                schema=simple_error_schema,
                example={
                    "error": "Failed to create API key",
                    "details": "Some error message"
                }
            )
        }
    )
    def post(self, request):
        """Create new API key"""
        name = request.data.get('name', 'Default API Key Name')
        user_id = request.data.get('user_id')

        if not user_id:
            return Response({
                "error": "The 'user_id' is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get user or throw error if not found
            user, created = AuthUser.objects.get_or_create(
                id=user_id,
                defaults={'email': f'{user_id}@api.com'}
            )
         
            # Create API key
            api_key = APIKey.objects.create(
                name=name,
                user=user
            )

            # Add api key expiration
            api_key.set_expiration()

            # Deactivate old API keys
            APIKey.objects.filter(user=user, is_active=True).exclude(id=api_key.id).update(is_active=False)

            return Response({
                "message": "API Key created successfully",
                "api_key": api_key.key,
                "name": api_key.name,
                "user_id": user.id,
                "expires_at": api_key.expires_at,
                "created_at": api_key.created_at.isoformat()
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "error": "Failed to create API key",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# User View
class UserListView(APIView):
    """API View for managing users"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['👤 User Management'],
        operation_summary="List all users with wallet balances",
        operation_description="Requirement 1: Fetch all users details (name, email, phone) along with their wallet balance",
        manual_parameters=[
            openapi.Parameter(
                'X-API-Key',
                openapi.IN_HEADER,
                description="API Key for authentication (Required)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="List of users with wallet balances",
                schema=user_list_response_schema,
                example={
                    "message": "Users retrieved successfully",
                    "count": 2,
                    "users": [
                        {
                            "id": 1,
                            "name": "Luv King",
                            "email": "luv@king.com",
                            "phone": "+9770000000",
                            "wallet_balance": "150.50",
                            "created_at": "2025-09-01T01:55:00Z"
                        }
                    ]
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                schema=auth_error_schema,
                example={
                    "detail": "Invalid API Key"
                }
            ),
            429: openapi.Response(
                description="Rate limit exceeded",
                schema=rate_limit_error_schema,
                example={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Limit: 100 per 3600 seconds"
                }
            )
        }
    )
    def get(self, request):
        """List Users API – Fetch all users details with authentication"""
        users = User.objects.all().select_related('wallet').order_by('name')
        serializer = UserSerializer(users, many=True)

        return Response({
            "message": "Users retrieved successfully",
            "count": len(serializer.data),
            "users": serializer.data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=['👤 User Management'],
        operation_summary="Create a new user",
        operation_description="Create a new user with automatic wallet creation",
        manual_parameters=[
            openapi.Parameter(
                'X-API-Key',
                openapi.IN_HEADER,
                description="API Key for authentication (Required)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        request_body=UserCreateSerializer,
        responses={
            201: openapi.Response(
                description="User created successfully",
                schema=user_create_response_schema,
                example={
                    "message": "User created successfully",
                    "user": {
                        "id": 2,
                        "name": "Jane Doe",
                        "email": "jane@doe.com",
                        "phone": "+9771111111",
                        "wallet_balance": "0.00",
                        "created_at": "2025-09-01T01:59:00Z"
                    }
                }
            ),
            400: openapi.Response(
                description="Invalid data",
                schema=simple_error_schema,
                example={
                    "error": "Invalid data provided",
                    "details": {"email": ["This field is required."]}
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                schema=auth_error_schema,
                example={
                    "detail": "Invalid API Key"
                }
            ),
            429: openapi.Response(
                description="Rate limit exceeded",
                schema=rate_limit_error_schema,
                example={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Limit: 100 per 3600 seconds"
                }
            )
        }
    )
    def post(self, request):
        """Create new user with authentication"""
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "error": "Invalid data provided",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        response_serializer = UserSerializer(user)

        return Response({
            "message": "User created successfully",
            "user": response_serializer.data
        }, status=status.HTTP_201_CREATED)

# User Wallet View
class UpdateWalletView(APIView):
    """API View for updating wallet balance"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['💰 Wallet Management'],
        operation_summary="Update user's wallet balance",
        operation_description="Requirement 2: Add or update an amount in any particular user's wallet",
        manual_parameters=[
            openapi.Parameter(
                'X-API-Key',
                openapi.IN_HEADER,
                description="API Key for authentication (Required)",
                type=openapi.TYPE_STRING,
                required=True
            ),
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
                description="Wallet updated",
                schema=wallet_update_response_schema,
                example={
                    "message": "Added $100 to John Doe's wallet",
                    "user": "John Doe",
                    "user_id": 1,
                    "user_email": "john@example.com",
                    "transaction_type": "CREDIT",
                    "amount": "100.00",
                    "previous_balance": "50.00",
                    "new_balance": "150.00",
                    "description": "Deposit via bank",
                    "transaction_id": 10,
                    "timestamp": "2025-09-01T02:01:00Z"
                }
            ),
            400: openapi.Response(
                description="Invalid request or insufficient funds",
                schema=simple_error_schema,
                example={
                    "error": "Insufficient funds",
                    "current_balance": "50.00",
                    "requested_amount": "100.00",
                    "shortfall": "50.00"
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                schema=auth_error_schema,
                example={
                    "detail": "Invalid API Key"
                }
            ),
            404: openapi.Response(
                description="User not found",
                schema=simple_error_schema,
                example={
                    "error": "User not found"
                }
            ),
            429: openapi.Response(
                description="Rate limit exceeded",
                schema=rate_limit_error_schema,
                example={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Limit: 100 per 3600 seconds"
                }
            ),
            500: openapi.Response(
                description="Internal error",
                schema=simple_error_schema,
                example={
                    "error": "Failed to update wallet",
                    "message": "Some error message"
                }
            )
        }
    )
    def put(self, request, user_id):
        """Update Wallet API with authentication and validation"""
        user = get_object_or_404(User, id=user_id)

        serializer = UpdateWalletSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "error": "Invalid request data",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        amount = validated_data['amount']
        transaction_type = validated_data['transaction_type']
        description = validated_data.get('description', '')

        previous_balance = user.wallet.balance

        try:
            with transaction.atomic():
                wallet = user.wallet

                if transaction_type == 'CREDIT':
                    wallet.add_funds(amount, description or f"Added ${amount} to wallet")
                    action_message = f"Added ${amount} to {user.name}'s wallet"
                elif transaction_type == 'DEBIT':
                    if wallet.balance < amount:
                        return Response({
                            "error": "Insufficient funds",
                            "current_balance": str(wallet.balance),
                            "requested_amount": str(amount),
                            "shortfall": str(amount - wallet.balance)
                        }, status=status.HTTP_400_BAD_REQUEST)

                    wallet.deduct_funds(amount, description or f"Deducted ${amount} from wallet")
                    action_message = f"Deducted ${amount} from {user.name}'s wallet"

                wallet.refresh_from_db()
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

# User Transactions View
class UserTransactionsView(APIView):
    """API View for fetching user's transaction history"""
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['📊 Transaction Management'],
        operation_summary="Get user's transaction history",
        operation_description="Requirement 3: Fetch all wallet transactions for a specific user by passing their user_id",
        manual_parameters=[
            openapi.Parameter(
                'X-API-Key',
                openapi.IN_HEADER,
                description="API Key for authentication (Required)",
                type=openapi.TYPE_STRING,
                required=True
            ),
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
                description="Transaction history",
                schema=transactions_response_schema,
                example={
                    "message": "Transactions retrieved successfully",
                    "user": {
                        "id": 1,
                        "name": "Luv King",
                        "email": "luv@king.com",
                        "phone": "+9770000000",
                        "current_balance": "120.00"
                    },
                    "summary": {
                        "total_transactions": 10,
                        "filtered_count": 2,
                        "total_credits": "250.00",
                        "total_debits": "130.00",
                        "net_balance": "120.00"
                    },
                    "filters_applied": {
                        "transaction_type": "ALL",
                        "limit": 50
                    },
                    "transactions": [
                        {
                            "id": 21,
                            "amount": "100.00",
                            "transaction_type": "CREDIT",
                            "description": "Deposit",
                            "timestamp": "2025-09-01T02:20:00Z"
                        }
                    ]
                }
            ),
            401: openapi.Response(
                description="Authentication required",
                schema=auth_error_schema,
                example={
                    "detail": "Invalid API Key"
                }
            ),
            404: openapi.Response(
                description="User not found",
                schema=simple_error_schema,
                example={
                    "error": "User not found"
                }
            ),
            429: openapi.Response(
                description="Rate limit exceeded",
                schema=rate_limit_error_schema,
                example={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Limit: 100 per 3600 seconds"
                }
            )
        }
    )
    def get(self, request, user_id):
        """Fetch Transactions API with authentication"""
        user = get_object_or_404(User, id=user_id)

        transaction_type = request.query_params.get('transaction_type', '').upper()
        limit = request.query_params.get('limit', '50')

        try:
            limit = int(limit)
            if limit <= 0:
                limit = 50
        except ValueError:
            limit = 50

        transactions_query = Transaction.objects.filter(
            wallet=user.wallet
        ).order_by('-timestamp')

        if transaction_type and transaction_type in ['CREDIT', 'DEBIT']:
            filtered_transactions = transactions_query.filter(transaction_type=transaction_type)
        else:
            filtered_transactions = transactions_query

        transactions = filtered_transactions[:limit]

        all_transactions = transactions_query
        total_credits = sum([t.amount for t in all_transactions.filter(transaction_type='CREDIT')])
        total_debits = sum([t.amount for t in all_transactions.filter(transaction_type='DEBIT')])

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