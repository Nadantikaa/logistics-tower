import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Cookie, Depends, Header, HTTPException, Response, status

from app.config import (
    ACCESS_TOKEN_TTL_MINUTES,
    ADMIN_EMAILS,
    COOKIE_DOMAIN,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    GOOGLE_CLIENT_ID,
    GOOGLE_TOKENINFO_URL,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    PII_ENCRYPTION_KEY,
    REFRESH_TOKEN_TTL_DAYS,
)
from app.db import get_db

GOOGLE_ALLOWED_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
ACCESS_COOKIE_NAME = "logistics_ai_access"
REFRESH_COOKIE_NAME = "logistics_ai_refresh"


def _derive_key() -> bytes:
    digest = hashlib.sha256(PII_ENCRYPTION_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


fernet = Fernet(_derive_key())


def encrypt_pii(value: str) -> str:
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_pii(value: str) -> str:
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Failed to decrypt stored user data.") from exc


def hash_email_lookup(email: str) -> str:
    normalized = email.strip().lower()
    return hmac.new(PII_ENCRYPTION_KEY.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_refresh_token(token: str) -> str:
    return hmac.new(JWT_SECRET_KEY.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{base64.urlsafe_b64encode(salt).decode('utf-8')}${base64.urlsafe_b64encode(derived_key).decode('utf-8')}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        encoded_salt, encoded_hash = stored_hash.split("$", 1)
        salt = base64.urlsafe_b64decode(encoded_salt.encode("utf-8"))
        expected_hash = base64.urlsafe_b64decode(encoded_hash.encode("utf-8"))
    except ValueError:
        return False

    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return secrets.compare_digest(derived_key, expected_hash)


def utc_now() -> datetime:
    return datetime.now(UTC)


def assign_role(email: str, existing_role: str | None = None) -> str:
    if email.strip().lower() in ADMIN_EMAILS:
        return "admin"
    return existing_role or "user"


def _parse_google_response(payload: dict) -> dict:
    audience = payload.get("aud")
    email = payload.get("email")
    google_sub = payload.get("sub")
    name = payload.get("name") or email or "Google User"
    issuer = payload.get("iss")
    expiry = payload.get("exp")

    if not google_sub or not email:
        raise HTTPException(status_code=401, detail="Google identity token is missing required claims.")

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is not configured.")

    if audience != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Google identity token audience mismatch.")

    if issuer not in GOOGLE_ALLOWED_ISSUERS:
        raise HTTPException(status_code=401, detail="Google identity token issuer is invalid.")

    if payload.get("email_verified") not in ("true", True):
        raise HTTPException(status_code=401, detail="Google account email is not verified.")

    if expiry is None or int(expiry) <= int(datetime.now(UTC).timestamp()):
        raise HTTPException(status_code=401, detail="Google identity token is expired.")

    return {
        "google_sub": google_sub,
        "email": email.strip().lower(),
        "name": name.strip(),
    }


def _serialize_user_identity(row) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
    }


def _safe_user_payload(user: dict) -> dict:
    return {
        "id": user["id"],
        "role": user["role"],
        "display_name": "Admin Operator" if user["role"] == "admin" else "Control Tower User",
    }


def create_access_token(user: dict) -> tuple[str, str]:
    now = utc_now()
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, expires_at.isoformat()


def create_refresh_token(user_id: int) -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(48)
    token_family = secrets.token_urlsafe(24)
    expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    with get_db() as connection:
        connection.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, token_family, created_at, expires_at, revoked_at)
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (
                user_id,
                hash_refresh_token(raw_token),
                token_family,
                utc_now().isoformat(),
                expires_at.isoformat(),
            ),
        )
        connection.commit()
    return raw_token, expires_at.isoformat()


def rotate_refresh_token(raw_token: str) -> tuple[dict, str, str]:
    hashed = hash_refresh_token(raw_token)
    with get_db() as connection:
        row = connection.execute(
            """
            SELECT user_id, token_family, expires_at, revoked_at
            FROM refresh_tokens
            WHERE token_hash = ?
            """,
            (hashed,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid refresh token.")
        if row["revoked_at"] is not None:
            raise HTTPException(status_code=401, detail="Refresh token revoked.")
        if datetime.fromisoformat(row["expires_at"]) <= utc_now():
            raise HTTPException(status_code=401, detail="Refresh token expired.")

        connection.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE token_hash = ?",
            (utc_now().isoformat(), hashed),
        )

        next_raw_token = secrets.token_urlsafe(48)
        next_expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
        connection.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, token_family, created_at, expires_at, revoked_at)
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (
                row["user_id"],
                hash_refresh_token(next_raw_token),
                row["token_family"],
                utc_now().isoformat(),
                next_expires_at.isoformat(),
            ),
        )
        connection.commit()

    user = get_user_by_id(row["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")

    return user, next_raw_token, next_expires_at.isoformat()


def revoke_refresh_token(raw_token: str | None) -> None:
    if not raw_token:
        return
    with get_db() as connection:
        connection.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
            (utc_now().isoformat(), hash_refresh_token(raw_token)),
        )
        connection.commit()


def _set_cookie(response: Response, *, key: str, value: str, max_age: int) -> None:
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN or None,
        max_age=max_age,
        path="/",
    )


def _clear_cookie(response: Response, key: str) -> None:
    response.delete_cookie(
        key=key,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN or None,
        path="/",
    )


def issue_auth_cookies(response: Response, user: dict) -> dict[str, Any]:
    access_token, access_expires_at = create_access_token(user)
    refresh_token, refresh_expires_at = create_refresh_token(user["id"])
    _set_cookie(
        response,
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=ACCESS_TOKEN_TTL_MINUTES * 60,
    )
    _set_cookie(
        response,
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
    )
    return {
        "authenticated": True,
        "expires_at": access_expires_at,
        "refresh_expires_at": refresh_expires_at,
        "user": _safe_user_payload(user),
    }


def get_user_by_id(user_id: int):
    with get_db() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                role
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if not row:
        return None
    return _serialize_user_identity(row)


async def verify_google_id_token(id_token: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Unable to reach Google token verification service.") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google identity token.")

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Unexpected Google verification response.") from exc

    return _parse_google_response(payload)


def upsert_google_user(google_profile: dict) -> dict:
    now = utc_now().isoformat()
    encrypted_email = encrypt_pii(google_profile["email"])
    encrypted_name = encrypt_pii(google_profile["name"])

    with get_db() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE google_sub = ?",
            (google_profile["google_sub"],),
        ).fetchone()

        if existing:
            current = connection.execute(
                "SELECT role FROM users WHERE id = ?",
                (existing["id"],),
            ).fetchone()
            connection.execute(
                """
                UPDATE users
                SET email_encrypted = ?, name_encrypted = ?, role = ?, picture_url = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    encrypted_email,
                    encrypted_name,
                    assign_role(google_profile["email"], current["role"] if current else None),
                    None,
                    now,
                    existing["id"],
                ),
            )
            user_id = existing["id"]
        else:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    google_sub,
                    email_encrypted,
                    name_encrypted,
                    role,
                    picture_url,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    google_profile["google_sub"],
                    encrypted_email,
                    encrypted_name,
                    assign_role(google_profile["email"]),
                    None,
                    now,
                    now,
                ),
            )
            user_id = cursor.lastrowid

        connection.commit()

    return {
        "id": user_id,
        "role": assign_role(google_profile["email"]),
    }


def create_local_user(name: str, email: str, password: str) -> dict:
    normalized_email = email.strip().lower()
    email_lookup_hash = hash_email_lookup(normalized_email)
    now = utc_now().isoformat()
    role = assign_role(normalized_email)

    with get_db() as connection:
        existing = connection.execute(
            "SELECT user_id FROM local_credentials WHERE email_lookup_hash = ?",
            (email_lookup_hash,),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="An account with that email already exists.")

        cursor = connection.execute(
            """
            INSERT INTO users (
                google_sub,
                email_encrypted,
                name_encrypted,
                role,
                picture_url,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"local:{email_lookup_hash}",
                encrypt_pii(normalized_email),
                encrypt_pii(name.strip() or normalized_email),
                role,
                None,
                now,
                now,
            ),
        )
        user_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO local_credentials (
                user_id,
                email_lookup_hash,
                password_hash,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                email_lookup_hash,
                hash_password(password),
                now,
                now,
            ),
        )
        connection.commit()

        return {
            "id": user_id,
            "role": role,
        }


def authenticate_local_user(email: str, password: str) -> dict:
    normalized_email = email.strip().lower()
    email_lookup_hash = hash_email_lookup(normalized_email)

    with get_db() as connection:
        row = connection.execute(
            """
            SELECT
                users.id,
                users.role,
                local_credentials.password_hash
            FROM local_credentials
            JOIN users ON users.id = local_credentials.user_id
            WHERE local_credentials.email_lookup_hash = ?
            """,
            (email_lookup_hash,),
        ).fetchone()

    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return _serialize_user_identity(row)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization scheme.")
    return token


def _decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT.") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT type.")
    return payload


def require_auth(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
):
    token = access_cookie or (_extract_bearer_token(authorization) if authorization else None)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing access token.")

    payload = _decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid JWT payload.")

    user = get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return user


def safe_user_response(user: dict) -> dict:
    return _safe_user_payload(user)


def refresh_session(response: Response, refresh_cookie: str | None) -> dict[str, Any]:
    if not refresh_cookie:
        raise HTTPException(status_code=401, detail="Missing refresh token.")
    user, next_refresh_token, refresh_expires_at = rotate_refresh_token(refresh_cookie)
    access_token, access_expires_at = create_access_token(user)
    _set_cookie(
        response,
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=ACCESS_TOKEN_TTL_MINUTES * 60,
    )
    _set_cookie(
        response,
        key=REFRESH_COOKIE_NAME,
        value=next_refresh_token,
        max_age=REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
    )
    return {
        "authenticated": True,
        "expires_at": access_expires_at,
        "refresh_expires_at": refresh_expires_at,
        "user": _safe_user_payload(user),
    }


def clear_auth_cookies(response: Response, refresh_cookie: str | None) -> None:
    revoke_refresh_token(refresh_cookie)
    _clear_cookie(response, ACCESS_COOKIE_NAME)
    _clear_cookie(response, REFRESH_COOKIE_NAME)
