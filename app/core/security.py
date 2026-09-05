from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_mfa_pending_token(data: dict) -> str:
    """Short-lived token issued after password verification but before
    MFA verification completes - roadmap's Auth/MFA. Deliberately a
    distinct 'type' from access/refresh tokens (enforced in
    get_current_user below) so it can't be used to authenticate normal
    API calls even though it's a validly-signed JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=5)
    to_encode.update({"exp": expire, "type": "mfa_pending"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from app.models.user import User
    payload = decode_token(token)
    # Only an "access" token may authenticate API calls - without this
    # check, a refresh token (7-day validity, meant only for the
    # /refresh endpoint) or the new short-lived mfa_pending token could
    # both be used directly as bearer tokens, defeating the point of
    # having separate token types at all.
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("scope") == "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Patient portal accounts cannot access staff endpoints")
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_roles(*roles):
    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}"
            )
        return current_user
    return role_checker


# ── Patient Portal auth — intentionally separate identity domain from staff `users`.
# A patient token carries scope="patient" and a patient_account_id; it is never
# accepted by get_current_user, and a staff token is never accepted here, so a
# portal breach can't laterally reach staff-only routes or vice versa.
def create_patient_access_token(patient_account_id: int, patient_id: int) -> str:
    to_encode = {
        "sub": str(patient_account_id),
        "patient_id": patient_id,
        "scope": "patient",
        "type": "access",
    }
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_patient(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from app.models.patient_portal import PatientAccount
    payload = decode_token(token)
    if payload.get("scope") != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="This endpoint is for patient portal accounts only")
    account_id = payload.get("sub")
    if account_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    account = db.query(PatientAccount).filter(
        PatientAccount.id == int(account_id), PatientAccount.is_active == True
    ).first()
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Patient account not found")
    return account
