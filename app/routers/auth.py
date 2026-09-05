from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, create_mfa_pending_token, decode_token, get_current_user, require_roles
)
from app.core.totp import generate_totp_secret, get_totp_uri, get_qr_code_base64, verify_totp_code
from app.models.user import User, UserRole
from app.models.admin import AuditLog
from app.models.doctor import DoctorProfile
from app.models.hr import StaffProfile
from app.schemas.auth import (
    UserCreate, UserResponse, LoginRequest, TokenResponse, ChangePasswordRequest, UserUpdate,
    MFARequiredResponse, MFASetupResponse, MFAConfirmRequest, MFADisableRequest, MFALoginVerifyRequest,
)
from app.core.rate_limit import limiter
from app.core.id_generator import next_sequence_number, MAX_RETRIES

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def generate_employee_id(role: UserRole, count: int) -> str:
    prefix_map = {
        UserRole.DOCTOR: "DR", UserRole.NURSE: "NR",
        UserRole.RECEPTIONIST: "RC", UserRole.PHARMACIST: "PH",
        UserRole.LAB_TECHNICIAN: "LT", UserRole.RADIOLOGIST: "RA",
        UserRole.ACCOUNTANT: "AC", UserRole.HR: "HR", UserRole.ADMIN: "AD"
    }
    prefix = prefix_map.get(role, "EM")
    return f"{prefix}{count:04d}"


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    from sqlalchemy.exc import IntegrityError

    emp_attempt_base = next_sequence_number(db, User, filters={"role": data.role})
    doc_attempt_base = next_sequence_number(db, DoctorProfile) if data.role == UserRole.DOCTOR else None
    staff_attempt_base = next_sequence_number(db, StaffProfile) if data.role in (
        UserRole.NURSE, UserRole.RECEPTIONIST, UserRole.PHARMACIST,
        UserRole.LAB_TECHNICIAN, UserRole.RADIOLOGIST,
        UserRole.ACCOUNTANT, UserRole.HR
    ) else None

    user = None
    last_error = None
    for i in range(MAX_RETRIES):
        employee_id = generate_employee_id(data.role, emp_attempt_base + i)
        user = User(
            employee_id=employee_id,
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            role=data.role,
            phone=data.phone,
            department=data.department
        )
        db.add(user)
        try:
            db.flush()  # user.id get பண்ணு, commit பண்ணல

            if doc_attempt_base is not None:
                profile = DoctorProfile(
                    user_id=user.id,
                    registration_number=f"REG{doc_attempt_base + i:05d}",
                    specialization=data.department or "General Medicine",
                )
                db.add(profile)
                db.flush()
            elif staff_attempt_base is not None:
                staff = StaffProfile(
                    user_id=user.id,
                    employee_code=user.employee_id,
                    date_of_joining=date.today(),
                )
                db.add(staff)
                db.flush()

            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            user = None
    if last_error:
        raise last_error

    db.commit()
    db.refresh(user)
    return user


@router.post("/login")
@limiter.limit("10/minute")
async def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    if user.mfa_enabled:
        # Password was correct, but login isn't complete - the person
        # must still submit a valid TOTP code via /auth/mfa/verify-login
        # before any access/refresh token is issued.
        mfa_token = create_mfa_pending_token({"sub": str(user.id)})
        return MFARequiredResponse(mfa_token=mfa_token)

    user.last_login = datetime.utcnow()
    audit = AuditLog(user_id=user.id, action="LOGIN", resource="auth",
                     ip_address=get_real_ip(request))
    db.add(audit)
    db.commit()

    token_data = {"sub": str(user.id), "role": user.role.value, "email": user.email}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=user
    )


@router.post("/mfa/verify-login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def mfa_verify_login(data: MFALoginVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """Second step of login when MFA is enabled: exchange a valid
    mfa_pending token + correct TOTP code for real access/refresh tokens."""
    payload = decode_token(data.mfa_token)
    if payload.get("type") != "mfa_pending":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MFA session")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA session")

    if not verify_totp_code(user.mfa_secret, data.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication code")

    user.last_login = datetime.utcnow()
    audit = AuditLog(user_id=user.id, action="LOGIN", resource="auth",
                     ip_address=get_real_ip(request))
    db.add(audit)
    db.commit()

    token_data = {"sub": str(user.id), "role": user.role.value, "email": user.email}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=user
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Generates a new TOTP secret and QR code for the current user to scan
    into an authenticator app. Deliberately does NOT enable MFA yet -
    the secret is stored but mfa_enabled stays False until /mfa/confirm
    proves the person can actually generate valid codes with it. Without
    this two-step flow, a typo'd or unscanned QR code could permanently
    lock someone out on next login.
    """
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled - disable it first to reconfigure")

    secret = generate_totp_secret()
    current_user.mfa_secret = secret
    db.commit()

    uri = get_totp_uri(secret, current_user.email)
    qr_code = get_qr_code_base64(uri)
    return MFASetupResponse(secret=secret, qr_code=qr_code, otpauth_uri=uri)


@router.post("/mfa/confirm")
async def mfa_confirm(data: MFAConfirmRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Completes MFA setup - proves the person's authenticator app
    actually has a working copy of the secret before turning MFA on."""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="No MFA setup in progress - call /mfa/setup first")
    if current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is already enabled")

    if not verify_totp_code(current_user.mfa_secret, data.code):
        raise HTTPException(status_code=400, detail="Invalid authentication code")

    current_user.mfa_enabled = True
    db.commit()
    return {"detail": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def mfa_disable(data: MFADisableRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Disabling MFA requires BOTH the account password and a valid
    current TOTP code - either alone isn't enough, since the whole point
    of MFA is that a leaked password alone shouldn't be able to turn off
    the second factor protecting the account."""
    if not current_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    if not verify_totp_code(current_user.mfa_secret, data.code):
        raise HTTPException(status_code=401, detail="Invalid authentication code")

    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.commit()
    return {"detail": "MFA disabled"}


@router.post("/refresh")
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    return {"access_token": create_access_token(token_data), "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    return db.query(User).all()


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user