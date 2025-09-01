Wallet Management API - Complete Usage Guide

Create Your API Key 🔑
Endpoint: POST /api/api-keys/create/
Give {
  "name": "My Test Key",
  "user_id": "testuser123"
}


👤 User Management
Create a New User
Endpoint: POST /api/users/

Required: X-API-Key: your_api_key_here
{
  "name": "luvking",
  "email": "luv@example.com",
  "phone": "+1234567890"
}


List All Users
Endpoint: GET /api/users/

Headers Required: Required: X-API-Key: your_api_key_here

Responce with the user list


💰 Wallet Management
Add Money to User's Wallet (Credit)
Endpoint: PUT /api/wallets/{user_id}/update/
Headers Required: Required: X-API-Key: your_api_key_here

{
  "transaction_type": "CREDIT",
  "amount": 100.50,
  "description": "Initial deposit"
}


Remove Money from User's Wallet (Debit)
Endpoint: PUT /api/wallets/{user_id}/update/
Headers Required: Required: X-API-Key: your_api_key_here

{
  "transaction_type": "DEBIT",
  "amount": 25.00,
  "description": "Purchase payment"
}
