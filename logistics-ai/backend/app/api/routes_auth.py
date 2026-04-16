from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel, Field, field_validator

from app.config import MFA_ENABLED
from app.security import (
    authenticate_local_user,
    clear_auth_cookies,
    create_local_user,
    get_optional_auth_user,
    issue_mfa_challenge,
    issue_auth_cookies,
    refresh_session,
    resend_mfa_challenge,
    safe_user_response,
    upsert_google_user,
    verify_mfa_challenge,
    verify_google_id_token,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: str


class MfaVerifyRequest(BaseModel):
    challenge_id: str
    otp_code: str = Field(min_length=6, max_length=6)

    @field_validator("otp_code")
    @classmethod
    def validate_otp_code(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) != 6 or not normalized.isdigit():
            raise ValueError("Enter the 6-digit verification code.")
        return normalized


class MfaResendRequest(BaseModel):
    challenge_id: str


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


def _build_auth_response(response: Response, user: dict, *, email: str, purpose: str) -> dict:
    if MFA_ENABLED:
        return issue_mfa_challenge(user=user, email=email, purpose=purpose)
    return issue_auth_cookies(response, user)


@router.post("/google")
async def login_with_google(payload: GoogleLoginRequest, response: Response):
    google_profile = await verify_google_id_token(payload.credential)
    user = upsert_google_user(google_profile)
    return _build_auth_response(response, user, email=google_profile["email"], purpose="google_login")


@router.post("/signup")
def signup_with_email(payload: EmailPasswordSignupRequest, response: Response):
    user = create_local_user(payload.name, payload.email, payload.password)
    return _build_auth_response(response, user, email=payload.email, purpose="signup")


@router.post("/login")
def login_with_email(payload: EmailPasswordLoginRequest, response: Response):
    user = authenticate_local_user(payload.email, payload.password)
    return _build_auth_response(response, user, email=payload.email, purpose="login")


@router.post("/mfa/verify")
def verify_otp(payload: MfaVerifyRequest, response: Response):
    return verify_mfa_challenge(response=response, challenge_id=payload.challenge_id, otp_code=payload.otp_code)


@router.post("/mfa/resend")
def resend_otp(payload: MfaResendRequest):
    return resend_mfa_challenge(payload.challenge_id)


@router.post("/refresh")
def refresh_auth_session(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias="logistics_ai_refresh"),
):
    return refresh_session(response, refresh_cookie)


@router.get("/me")
def get_current_user(user=Depends(get_optional_auth_user)):
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "expires_at": "",
        "refresh_expires_at": "",
        "user": safe_user_response(user),
    }


@router.post("/logout")
def logout(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias="logistics_ai_refresh"),
):
    clear_auth_cookies(response, refresh_cookie)
    return {"status": "logged_out"}
