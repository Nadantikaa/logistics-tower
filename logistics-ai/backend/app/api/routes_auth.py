from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel, Field, field_validator

from app.config import MFA_ENABLED
from app.security import (
    authenticate_local_user,
    clear_auth_cookies,
    create_local_user,
    issue_auth_cookies,
    issue_mfa_challenge,
    require_auth,
    resend_mfa_challenge,
    refresh_session,
    safe_user_response,
    upsert_google_user,
    verify_mfa_challenge,
    verify_google_id_token,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: str


class EmailPasswordSignupRequest(BaseModel):
    name: str = Field(default="", max_length=100)
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return normalized


class EmailPasswordLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return normalized


class MfaVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=12, max_length=128)
    otp_code: str = Field(min_length=6, max_length=6)

    @field_validator("otp_code")
    @classmethod
    def validate_otp_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit():
            raise ValueError("Enter the 6-digit verification code.")
        return normalized


class MfaResendRequest(BaseModel):
    challenge_id: str = Field(min_length=12, max_length=128)


def _build_auth_response(response: Response, user: dict) -> dict:
    return issue_auth_cookies(response, user)


@router.post("/google")
async def login_with_google(payload: GoogleLoginRequest, response: Response):
    google_profile = await verify_google_id_token(payload.credential)
    user = upsert_google_user(google_profile)
    if not MFA_ENABLED:
        return _build_auth_response(response, user)
    return issue_mfa_challenge(user=user, email=google_profile["email"], purpose="google_login")


@router.post("/signup")
def signup_with_email(payload: EmailPasswordSignupRequest, response: Response):
    user = create_local_user(payload.name, payload.email, payload.password)
    if not MFA_ENABLED:
        return _build_auth_response(response, user)
    return issue_mfa_challenge(user=user, email=payload.email, purpose="signup")


@router.post("/login")
def login_with_email(payload: EmailPasswordLoginRequest, response: Response):
    user = authenticate_local_user(payload.email, payload.password)
    if not MFA_ENABLED:
        return _build_auth_response(response, user)
    return issue_mfa_challenge(user=user, email=payload.email, purpose="login")


@router.post("/mfa/verify")
def verify_mfa(payload: MfaVerifyRequest, response: Response):
    return verify_mfa_challenge(response, payload.challenge_id, payload.otp_code)


@router.post("/mfa/resend")
def resend_mfa(payload: MfaResendRequest):
    return resend_mfa_challenge(payload.challenge_id)


@router.post("/refresh")
def refresh_auth_session(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias="logistics_ai_refresh"),
):
    return refresh_session(response, refresh_cookie)


@router.get("/me")
def get_current_user(user=Depends(require_auth)):
    return safe_user_response(user)


@router.post("/logout")
def logout(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias="logistics_ai_refresh"),
):
    clear_auth_cookies(response, refresh_cookie)
    return {"status": "logged_out"}
