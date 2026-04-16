"""
Authentication routes for user registration and login.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger("myapp")

from app.models.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    RegistrationResponse,
    LoginResponse,
    UserResponse,
    ErrorResponse,
)
from app.models.user import User
from app.security import hash_password, verify_password, create_access_token
from app.encryption import encrypt_email, hash_email, decrypt_email
from app.database import get_db_session
from app.config import JWT_EXPIRATION_HOURS

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input or user already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db_session),
) -> RegistrationResponse:
    """
    Register a new user account.
    
    **Input validation:**
    - Email must be valid format
    - Password must be strong (min 8 chars, uppercase, lowercase, digit, special char)
    - Full name must be 2-255 characters
    
    **Security:**
    - Password is hashed with bcrypt (12 rounds)
    - Email is encrypted before storage
    - Email hash is stored for lookups without decryption
    - Response contains NO sensitive data
    
    **Example request:**
    ```json
    {
        "full_name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123!"
    }
    ```
    """
    
    logger.info(f"Registration attempt for email: {request.email}")
    
    # Check if email already exists
    email_hash = hash_email(request.email)
    existing_user = db.execute(
        select(User).where(User.email_hash == email_hash)
    ).scalars().first()
    
    if existing_user:
        logger.warning(f"Registration failed: Email already registered - {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Check if username already exists
    username = request.email.split("@")[0]  # Use email prefix as username
    existing_username = db.execute(
        select(User).where(User.username == username)
    ).scalars().first()
    
    if existing_username:
        # Add random suffix if username taken
        import random
        username = f"{username}_{random.randint(1000, 9999)}"
    
    # Hash password
    password_hash = hash_password(request.password)
    
    # Encrypt email
    encrypted_email = encrypt_email(request.email)
    
    # Create new user
    user = User(
        username=username,
        email_hash=email_hash,
        encrypted_email=encrypted_email,
        password_hash=password_hash,
        full_name=request.full_name,
        role="viewer",  # Default role
        is_active=True,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"User registered successfully - ID: {user.id}, Email: {request.email}, Username: {user.username}")
    
    user_data = UserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )
    
    return RegistrationResponse(
        message="User registered successfully",
        user=user_data,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        404: {"model": ErrorResponse, "description": "User not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db_session),
) -> LoginResponse:
    """
    Login with email and password.
    
    **Returns:**
    - JWT access token (valid for 24 hours by default)
    - User information (NO password or email)
    
    **Token usage:**
    Add token to Authorization header: `Authorization: Bearer <token>`
    
    **Example request:**
    ```json
    {
        "email": "john@example.com",
        "password": "SecurePass123!"
    }
    ```
    """
    
    logger.info(f"Login attempt for email: {request.email}")
    
    # Find user by email hash
    email_hash = hash_email(request.email)
    user = db.execute(
        select(User).where(User.email_hash == email_hash)
    ).scalars().first()
    
    if not user:
        logger.warning(f"Login failed: User not found - {request.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"Login failed: Invalid credentials - {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    
    if not user.is_active:
        logger.warning(f"Login failed: User inactive - {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    
    logger.info(f"Login successful - User ID: {user.id}, Username: {user.username}")
    
    # Generate JWT token
    token = create_access_token(user.id, user.username, user.role)
    
    user_data = UserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )
    
    return LoginResponse(
        message="Login successful",
        access_token=token,
        token_type="Bearer",
        user=user_data,
        expires_in=JWT_EXPIRATION_HOURS * 3600,  # Convert hours to seconds
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(
    db: Session = Depends(get_db_session),
) -> UserResponse:
    """
    Get current authenticated user information.
    Requires valid JWT token in Authorization header.
    """
    # This endpoint requires authentication middleware
    # For now, return error - implement with JWT dependency injection
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
