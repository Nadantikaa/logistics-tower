import base64
import hashlib
import hmac
import json
import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
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
    MFA_FROM_EMAIL,
    MFA_MAX_ATTEMPTS,
    MFA_OTP_TTL_MINUTES,
    MFA_SMTP_HOST,
    MFA_SMTP_PASSWORD,
    MFA_SMTP_PORT,
    MFA_SMTP_USERNAME,
    MFA_SMTP_USE_TLS,
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


def hash_otp(challenge_id: str, otp_code: str) -> str:
    value = f"{challenge_id}:{otp_code}"
    return hmac.new(JWT_SECRET_KEY.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


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


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return email
    masked_local = (local[:2] + "*" * max(len(local) - 2, 0)) if len(local) > 2 else local[:1] + "*"
    domain_name, dot, suffix = domain.partition(".")
    masked_domain = (domain_name[:2] + "*" * max(len(domain_name) - 2, 0)) if len(domain_name) > 2 else domain_name[:1] + "*"
    return f"{masked_local}@{masked_domain}{dot}{suffix}"


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _mfa_expires_at() -> datetime:
    return utc_now() + timedelta(minutes=MFA_OTP_TTL_MINUTES)


def _send_mfa_email(email: str, otp_code: str, purpose: str, expires_at: datetime) -> bool:
    if not MFA_SMTP_HOST or not MFA_FROM_EMAIL:
        return False

    message = EmailMessage()
    message["Subject"] = "Your Logistics AI verification code"
    message["From"] = MFA_FROM_EMAIL
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Your verification code for {purpose.replace('_', ' ')} is {otp_code}.",
                f"It expires at {expires_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}.",
                "If you did not request this code, you can ignore this email.",
            ]
        )
    )

    with smtplib.SMTP(MFA_SMTP_HOST, MFA_SMTP_PORT, timeout=15) as smtp:
        if MFA_SMTP_USE_TLS:
            smtp.starttls()
        if MFA_SMTP_USERNAME:
            smtp.login(MFA_SMTP_USERNAME, MFA_SMTP_PASSWORD)
        smtp.send_message(message)
    return True


def _build_mfa_challenge_payload(challenge_id: str, email: str, expires_at: datetime, *, otp_code: str | None = None) -> dict:
    payload = {
        "mfa_required": True,
        "challenge_id": challenge_id,
        "email_hint": _mask_email(email),
        "expires_at": expires_at.isoformat(),
    }
    if otp_code is not None:
        payload["dev_otp_code"] = otp_code
    return payload


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


def issue_mfa_challenge(*, user: dict, email: str, purpose: str) -> dict[str, Any]:
    challenge_id = secrets.token_urlsafe(24)
    otp_code = _generate_otp()
    now = utc_now()
    expires_at = _mfa_expires_at()
    encrypted_email = encrypt_pii(email)

    with get_db() as connection:
        connection.execute(
            "UPDATE mfa_challenges SET consumed_at = ? WHERE user_id = ? AND consumed_at IS NULL",
            (now.isoformat(), user["id"]),
        )
        connection.execute(
            """
            INSERT INTO mfa_challenges (
                challenge_id,
                user_id,
                purpose,
                email_encrypted,
                otp_hash,
                created_at,
                expires_at,
                attempts,
                verified_at,
                consumed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL)
            """,
            (
                challenge_id,
                user["id"],
                purpose,
                encrypted_email,
                hash_otp(challenge_id, otp_code),
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )
        connection.commit()

    dev_otp_code = None
    try:
        email_sent = _send_mfa_email(email, otp_code, purpose, expires_at)
        if not email_sent:
            dev_otp_code = otp_code
    except smtplib.SMTPException:
        dev_otp_code = otp_code

    return _build_mfa_challenge_payload(challenge_id, email, expires_at, otp_code=dev_otp_code)


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


def _get_active_mfa_challenge(challenge_id: str):
    with get_db() as connection:
        row = connection.execute(
            """
            SELECT challenge_id, user_id, purpose, email_encrypted, otp_hash, created_at, expires_at, attempts, verified_at, consumed_at
            FROM mfa_challenges
            WHERE challenge_id = ?
            """,
            (challenge_id,),
        ).fetchone()
    return row


def verify_mfa_challenge(*, response: Response, challenge_id: str, otp_code: str) -> dict[str, Any]:
    row = _get_active_mfa_challenge(challenge_id)
    now = utc_now()
    if not row:
        raise HTTPException(status_code=404, detail="Verification challenge not found.")
    if row["consumed_at"] is not None or row["verified_at"] is not None:
        raise HTTPException(status_code=400, detail="Verification challenge is no longer active.")
    if datetime.fromisoformat(row["expires_at"]) <= now:
        raise HTTPException(status_code=401, detail="Verification code expired.")
    if row["attempts"] >= MFA_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many incorrect verification attempts.")

    if not secrets.compare_digest(row["otp_hash"], hash_otp(challenge_id, otp_code)):
        with get_db() as connection:
            next_attempts = row["attempts"] + 1
            consumed_at = now.isoformat() if next_attempts >= MFA_MAX_ATTEMPTS else None
            connection.execute(
                "UPDATE mfa_challenges SET attempts = ?, consumed_at = COALESCE(consumed_at, ?) WHERE challenge_id = ?",
                (next_attempts, consumed_at, challenge_id),
            )
            connection.commit()
        remaining = max(MFA_MAX_ATTEMPTS - (row["attempts"] + 1), 0)
        raise HTTPException(status_code=401, detail=f"Invalid verification code. {remaining} attempt(s) remaining.")

    user = get_user_by_id(row["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")

    with get_db() as connection:
        connection.execute(
            "UPDATE mfa_challenges SET verified_at = ?, consumed_at = ? WHERE challenge_id = ?",
            (now.isoformat(), now.isoformat(), challenge_id),
        )
        connection.commit()

    return issue_auth_cookies(response, user)


def resend_mfa_challenge(challenge_id: str) -> dict[str, Any]:
    row = _get_active_mfa_challenge(challenge_id)
    now = utc_now()
    if not row:
        raise HTTPException(status_code=404, detail="Verification challenge not found.")
    if row["consumed_at"] is not None or row["verified_at"] is not None:
        raise HTTPException(status_code=400, detail="Verification challenge is no longer active.")

    email = decrypt_pii(row["email_encrypted"])
    next_code = _generate_otp()
    expires_at = _mfa_expires_at()

    with get_db() as connection:
        connection.execute(
            """
            UPDATE mfa_challenges
            SET otp_hash = ?, created_at = ?, expires_at = ?, attempts = 0
            WHERE challenge_id = ?
            """,
            (
                hash_otp(challenge_id, next_code),
                now.isoformat(),
                expires_at.isoformat(),
                challenge_id,
            ),
        )
        connection.commit()

    dev_otp_code = None
    try:
        email_sent = _send_mfa_email(email, next_code, row["purpose"], expires_at)
        if not email_sent:
            dev_otp_code = next_code
    except smtplib.SMTPException:
        dev_otp_code = next_code

    return _build_mfa_challenge_payload(challenge_id, email, expires_at, otp_code=dev_otp_code)


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


def get_optional_auth_user(
    authorization: str | None = Header(default=None),
    access_cookie: str | None = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
):
    token = access_cookie or (_extract_bearer_token(authorization) if authorization else None)
    if not token:
        return None

    try:
        payload = _decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return get_user_by_id(int(user_id))
    except (HTTPException, ValueError):
        return None


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
