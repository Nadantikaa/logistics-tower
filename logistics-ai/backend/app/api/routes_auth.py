from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel, Field, field_validator

from app.security import (
    authenticate_local_user,
    clear_auth_cookies,
    create_local_user,
    issue_auth_cookies,
    require_auth,
    refresh_session,
    safe_user_response,
    upsert_google_user,
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


def _build_auth_response(response: Response, user: dict) -> dict:
    return issue_auth_cookies(response, user)


@router.post("/google")
async def login_with_google(payload: GoogleLoginRequest, response: Response):
    google_profile = await verify_google_id_token(payload.credential)
    user = upsert_google_user(google_profile)
    return _build_auth_response(response, user)


@router.post("/signup")
def signup_with_email(payload: EmailPasswordSignupRequest, response: Response):
    user = create_local_user(payload.name, payload.email, payload.password)
    return _build_auth_response(response, user)


@router.post("/login")
def login_with_email(payload: EmailPasswordLoginRequest, response: Response):
    user = authenticate_local_user(payload.email, payload.password)
    return _build_auth_response(response, user)


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
