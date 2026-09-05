from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    department: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    employee_id: str
    email: str
    full_name: str
    role: UserRole
    phone: Optional[str]
    department: Optional[str]
    photo_url: Optional[str] = None
    is_active: bool
    mfa_enabled: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class MFARequiredResponse(BaseModel):
    """Returned instead of TokenResponse when the account has MFA
    enabled - password was correct, but login isn't complete yet."""
    mfa_required: bool = True
    mfa_token: str  # short-lived, submit back to /auth/mfa/verify-login


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str  # base64 data URI
    otpauth_uri: str


class MFAConfirmRequest(BaseModel):
    code: str


class MFADisableRequest(BaseModel):
    password: str
    code: str


class MFALoginVerifyRequest(BaseModel):
    mfa_token: str
    code: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str