"""
Encryption utilities for protecting sensitive PII like email addresses.
Uses Fernet (AES-128) symmetric encryption from cryptography library.
"""

from cryptography.fernet import Fernet
from typing import Optional
import base64
import hashlib

from app.config import ENCRYPTION_KEY


def _get_cipher():
    """
    Create a Fernet cipher from the encryption key.
    Ensures key is properly formatted (base64-encoded 32 bytes).
    """
    # Pad or truncate key to 32 bytes, then base64 encode for Fernet
    key_bytes = ENCRYPTION_KEY.encode()[:32].ljust(32, b"0")
    key_b64 = base64.urlsafe_b64encode(hashlib.sha256(key_bytes).digest())
    return Fernet(key_b64)


def encrypt_email(email: str) -> str:
    """
    Encrypt an email address using Fernet symmetric encryption.
    
    Args:
        email: Plain text email address
        
    Returns:
        Encrypted email (safe to store in database)
    """
    cipher = _get_cipher()
    encrypted = cipher.encrypt(email.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_email(encrypted_email: str) -> Optional[str]:
    """
    Decrypt an encrypted email address.
    
    Args:
        encrypted_email: Encrypted email from database
        
    Returns:
        Plain text email if decryption succeeds, None otherwise
    """
    try:
        cipher = _get_cipher()
        decrypted = cipher.decrypt(encrypted_email.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        return None


def hash_email(email: str) -> str:
    """
    Create a searchable hash of email for lookups without decryption.
    Uses SHA-256 for consistent one-way hashing.
    
    Args:
        email: Plain text email address
        
    Returns:
        SHA-256 hash of email
    """
    return hashlib.sha256(email.lower().encode("utf-8")).hexdigest()
