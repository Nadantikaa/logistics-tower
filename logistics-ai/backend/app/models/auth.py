"""
Pydantic models for user authentication (request/response validation).
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRegisterRequest(BaseModel):
    """Request model for user registration."""
    
    full_name: str = Field(..., min_length=2, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=128, description="User's password")
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};:,.<>?]", v):
            raise ValueError("Password must contain at least one special character (!@#$%^&*...)")
        return v


class UserLoginRequest(BaseModel):
    """Request model for user login."""
    
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserResponse(BaseModel):
    """Response model for user data (NO sensitive fields)."""
    
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    last_login_at: str | None = None
    
    class Config:
        from_attributes = True


class RegistrationResponse(BaseModel):
    """Response model for successful registration."""
    
    message: str
    user: UserResponse
    

class LoginResponse(BaseModel):
    """Response model for successful login."""
    
    message: str
    access_token: str
    token_type: str = "Bearer"
    user: UserResponse
    expires_in: int = Field(..., description="Token expiration in seconds")


class ErrorResponse(BaseModel):
    """Response model for error cases."""
    
    detail: str
    error_code: str | None = None


class TokenPayload(BaseModel):
    """Payload structure for JWT tokens."""
    
    sub: str  # user_id
    username: str
    role: str
    iat: int  # issued at
    exp: int  # expiration time
