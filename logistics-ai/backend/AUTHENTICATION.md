# Secure User Authentication & Authorization

## Overview

The backend implements enterprise-grade security for user registration and login:

- **Password Hashing**: bcrypt with 12 salt rounds
- **Email Encryption**: Fernet (AES-128) symmetric encryption for PII
- **Email Hashing**: SHA-256 for searchable lookups without decryption
- **JWT Tokens**: HS256 signed tokens with configurable expiration
- **Input Validation**: Pydantic models with email format and password strength checks
- **Secure Responses**: No passwords or emails in API responses

---

## Quick Start

### 1. **Rebuild Docker with new dependencies**

```bash
docker-compose down -v
docker-compose up --build
```

The new database schema automatically updates with `email_hash` and `encrypted_email` fields.

### 2. **Register a User**

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "john",
    "full_name": "John Doe",
    "role": "viewer",
    "is_active": true,
    "created_at": "2026-04-16T10:30:00",
    "last_login_at": null
  }
}
```

**Note:** Email is NOT returned in response for security.

### 3. **Login**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "user": {
    "id": 1,
    "username": "john",
    "full_name": "John Doe",
    "role": "viewer",
    "is_active": true,
    "created_at": "2026-04-16T10:30:00",
    "last_login_at": "2026-04-16T10:35:22"
  },
  "expires_in": 86400
}
```

---

## Password Requirements

Passwords must be:
- **Minimum 8 characters**
- **At least one uppercase letter** (A-Z)
- **At least one lowercase letter** (a-z)
- **At least one digit** (0-9)
- **At least one special character** (!@#$%^&*()_+-=[]{}...etc)

### Valid Example:
```
SecurePass123!
Password@2026
MyApp#456Token
```

### Invalid Examples:
```
password123!      ❌ No uppercase
PASSWORD123!      ❌ No lowercase
Securepass!       ❌ No digit
SecurePass123     ❌ No special character
Short@1           ❌ Too short (< 8 chars)
```

---

## Security Architecture

### **1. Password Hashing with bcrypt**

```python
from app.security import hash_password, verify_password

# Registration
plain_password = "SecurePass123!"
hashed = hash_password(plain_password)
# Stored in DB: $2b$12$KIXxPfxeKo.B.jgR5hkTCO...

# Login
is_valid = verify_password("SecurePass123!", hashed)  # True
is_valid = verify_password("WrongPass123!", hashed)   # False
```

**Why bcrypt?**
- Adaptive hashing with salt rounds (currently 12)
- Computationally expensive (slows brute-force attacks)
- Resistant to GPU/ASIC attacks
- Industry standard for password storage

### **2. Email Encryption (Fernet)**

```python
from app.encryption import encrypt_email, decrypt_email, hash_email

email = "john@example.com"

# Encrypt for storage
encrypted = encrypt_email(email)
# Stored: gAAAAABkL3x9hJkZ9Z...

# Hash for lookups
email_hash = hash_email(email)
# Stored: a1b2c3d4e5f6... (SHA-256)

# Decrypt (only when needed)
decrypted = decrypt_email(encrypted)  # "john@example.com"
```

**Why this approach?**
- `encrypted_email`: Allows decryption if needed (full PII protection)
- `email_hash`: Enables lookups without decrypting (privacy + performance)
- Fernet: Standard encryption from cryptography library

### **3. JWT Token Generation**

```python
from app.security import create_access_token, verify_token

# After successful login
token = create_access_token(
    user_id=1,
    username="john",
    role="viewer"
)
# Returns: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Token structure (decoded):
{
  "sub": "1",              # user_id
  "username": "john",
  "role": "viewer",
  "iat": 1713265800,       # issued at
  "exp": 1713352200        # expiration (24 hours later)
}

# Verify token
payload = verify_token(token)  # Returns dict if valid
payload = verify_token("invalid")  # Returns None
```

**Token Configuration:**
- Algorithm: HS256 (HMAC with SHA-256)
- Expiration: 24 hours (configurable in `.env`)
- Signature: Verified with JWT_SECRET_KEY

---

## Database Schema

### **users Table**

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,          -- login name
    email_hash VARCHAR(64) NOT NULL UNIQUE,         -- SHA-256 hash (searchable)
    encrypted_email TEXT NOT NULL,                  -- Fernet encrypted
    password_hash VARCHAR(512) NOT NULL,            -- bcrypt hashed
    full_name VARCHAR(255),
    role ENUM('admin', 'operator', 'viewer'),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email_hash (email_hash),
    INDEX idx_is_active (is_active)
);
```

**Key Fields:**
- `email_hash`: Unique, indexed for fast lookups (SHA-256)
- `encrypted_email`: Stores encrypted email for security
- `password_hash`: Never store plain passwords!
- `last_login_at`: Auto-updated on successful login

---

## API Endpoints

### **POST /auth/register**

Register a new user account.

**Request:**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

**Response (201 Created):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "john",
    "full_name": "John Doe",
    "role": "viewer",
    "is_active": true,
    "created_at": "2026-04-16T10:30:00",
    "last_login_at": null
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid input (weak password, invalid email)
- `400 Bad Request`: Email already registered
- `500 Internal Server Error`: Database error

---

### **POST /auth/login**

Authenticate and receive JWT token.

**Request:**
```json
{
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "user": {
    "id": 1,
    "username": "john",
    "full_name": "John Doe",
    "role": "viewer",
    "is_active": true,
    "created_at": "2026-04-16T10:30:00",
    "last_login_at": "2026-04-16T10:35:22"
  },
  "expires_in": 86400
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials
- `401 Unauthorized`: Account inactive
- `404 Not Found`: User not found

---

## Using JWT Tokens

### **Add Token to API Requests**

```bash
# After login, use the access_token in Authorization header
curl -X GET http://localhost:8000/api/shipments \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### **Token Structure**

```python
import jwt

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Decode (verify signature)
payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
# {
#   "sub": "1",
#   "username": "john",
#   "role": "viewer",
#   "iat": 1713265800,
#   "exp": 1713352200
# }

# Check expiration
import time
is_expired = payload["exp"] < time.time()  # False (still valid)
```

### **Token Refresh (TODO)**

Current implementation uses simple 24-hour tokens. For production, add:
- Refresh tokens (longer expiration)
- Token rotation
- Blacklist/revocation

---

## Environment Configuration

### **.env File**

```bash
# Security Keys (⚠️ Change in production!)
JWT_SECRET_KEY=your-secret-key-change-in-production-min-32-chars-long!!!!
JWT_EXPIRATION_HOURS=24
ENCRYPTION_KEY=change-this-key-32-chars-min-for-production!!!!!

# Database
DB_HOST=db
DB_USER=logistics_user
DB_PASSWORD=logistics_password
DB_NAME=logistics_db
```

### **Production Setup**

1. **Generate strong keys:**
   ```bash
   # JWT_SECRET_KEY (Python)
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # ENCRYPTION_KEY
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Update .env:**
   ```bash
   JWT_SECRET_KEY=your_generated_key_here
   ENCRYPTION_KEY=your_generated_key_here
   JWT_EXPIRATION_HOURS=24
   ```

3. **Restart services:**
   ```bash
   docker-compose restart backend
   ```

---

## Testing

### **Python Test Client**

```python
import httpx

BASE_URL = "http://localhost:8000"
client = httpx.Client()

# Register
register_response = client.post(
    f"{BASE_URL}/auth/register",
    json={
        "full_name": "Jane Smith",
        "email": "jane@example.com",
        "password": "TestPass123!"
    }
)
print(register_response.json())

# Login
login_response = client.post(
    f"{BASE_URL}/auth/login",
    json={
        "email": "jane@example.com",
        "password": "TestPass123!"
    }
)
data = login_response.json()
token = data["access_token"]
print(f"Token: {token}")

# Use token in request
headers = {"Authorization": f"Bearer {token}"}
protected_response = client.get(
    f"{BASE_URL}/api/shipments",
    headers=headers
)
print(protected_response.json())
```

### **cURL Tests**

```bash
# Test 1: Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Test 2: Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }' | jq '.access_token'

# Save token to variable
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }' | jq -r '.access_token')

# Test 3: Use token
curl -X GET http://localhost:8000/api/shipments \
  -H "Authorization: Bearer $TOKEN"

# Test 4: Invalid password
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "WrongPassword123!"
  }'
# Returns: {"detail": "Invalid credentials"}

# Test 5: Weak password
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Bad User",
    "email": "bad@example.com",
    "password": "weak"
  }'
# Returns: {"detail": "Password must be at least 8 characters..."}
```

---

## Security Checklist

- ✅ Passwords hashed with bcrypt (12 rounds)
- ✅ Emails encrypted with Fernet before storage
- ✅ Email hashes for searchable lookups
- ✅ JWT tokens signed with secret key
- ✅ Input validation (email format, password strength)
- ✅ Sensitive data NOT exposed in responses
- ✅ Last login tracking
- ✅ Active/inactive user status
- ⚠️ TODO: Refresh tokens
- ⚠️ TODO: Password reset flow
- ⚠️ TODO: Account lockout after failed attempts
- ⚠️ TODO: Rate limiting on auth endpoints
- ⚠️ TODO: Two-factor authentication (2FA)

---

## Next Steps

### **1. Add Authentication Middleware**

Create dependency for FastAPI to check JWT tokens:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return payload

# Use in endpoints:
@router.get("/protected")
def protected_endpoint(payload = Depends(verify_token)):
    return {"user_id": payload["sub"]}
```

### **2. Add Role-Based Access Control (RBAC)**

```python
def check_admin(payload = Depends(verify_token)):
    if payload["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return payload

@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin = Depends(check_admin)):
    # Only admins can delete users
    pass
```

### **3. Add Password Reset**

```python
@router.post("/auth/request-password-reset")
def request_password_reset(email: EmailStr):
    # Generate reset token
    # Send email with link
    pass

@router.post("/auth/reset-password")
def reset_password(token: str, new_password: str):
    # Verify token
    # Update password
    pass
```

### **4. Enable HTTPS**

```bash
# In production, use SSL certificates
docker-compose.yml:
  backend:
    command: uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

---

## File Structure

```
backend/
├── app/
│   ├── security.py              # ✅ Password hashing, JWT
│   ├── encryption.py            # ✅ Email encryption
│   ├── database.py              # ✅ SQLAlchemy session
│   ├── config.py                # ✅ Updated with JWT/encryption keys
│   ├── main.py                  # ✅ Updated with auth router
│   ├── models/
│   │   ├── auth.py              # ✅ Pydantic models (request/response)
│   │   └── user.py              # ✅ SQLAlchemy User model
│   └── api/
│       └── routes_auth.py       # ✅ Register & Login endpoints
├── init.sql                     # ✅ Updated schema
├── requirements.txt             # ✅ Added bcrypt, pyjwt, cryptography
├── docker-compose.yml           # (unchanged)
└── .env.example                 # ✅ Updated with keys
```

---

## Troubleshooting

### **"Email already registered"**
- Email already exists in database
- Check: `docker-compose exec db mysql -u root -proot_password -e "SELECT email_hash FROM logistics_db.users;"`

### **"Password must contain..."**
- Password doesn't meet strength requirements
- Must have: uppercase, lowercase, digit, special character, 8+ chars

### **"Invalid credentials"**
- Email or password is wrong
- Check MySQL to verify email_hash exists

### **"User not found"**
- User never registered
- Check: `docker-compose exec db mysql -u root -proot_password -e "SELECT username FROM logistics_db.users;"`

### **JWT Token Errors**
- Token expired: Get new token by logging in again
- Invalid token: Check Authorization header format
- Missing token: Add `Authorization: Bearer <token>` header

---

## References

- [bcrypt documentation](https://pypi.org/project/bcrypt/)
- [PyJWT documentation](https://pyjwt.readthedocs.io/)
- [Cryptography Fernet](https://cryptography.io/en/latest/fernet/)
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
