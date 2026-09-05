from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.organization import Branch, TaxRate, PaymentModeMaster
from app.models.user import User, UserRole
from app.models.doctor import DoctorProfile
from app.models.hr import StaffProfile
from app.schemas.organization import (
    BranchCreate, BranchUpdate, BranchResponse,
    TaxRateCreate, TaxRateResponse,
    PaymentModeMasterCreate, PaymentModeMasterResponse,
)
from app.schemas.unified_staff import UnifiedStaffEntry, LinkDoctorToStaffRequest

router = APIRouter(prefix="/organization", tags=["Organization & Master Data"])


# ── BRANCHES ─────────────────────────────────────────────

@router.post("/branches", response_model=BranchResponse, status_code=201)
async def create_branch(
    data: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    existing = db.query(Branch).filter(Branch.branch_code == data.branch_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="A branch with this code already exists")
    branch = Branch(**data.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.get("/branches", response_model=list[BranchResponse])
async def list_branches(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Branch)
    if active_only:
        q = q.filter(Branch.is_active == True)  # noqa: E712
    return q.order_by(Branch.name).all()


@router.put("/branches/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int,
    data: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(branch, field, value)
    db.commit()
    db.refresh(branch)
    return branch


# Department CRUD lives at /api/hr/departments (app/routers/hr.py) -
# a real, working Department table with a StaffProfile relationship
# already existed there. Rather than duplicating it here, this module
# only added the genuinely missing piece: linking departments to a
# Branch (see the department schema/model in hr.py for the branch_id
# field this module introduced).


# ── TAX RATE MASTER ─────────────────────────────────────────────

@router.post("/tax-rates", response_model=TaxRateResponse, status_code=201)
async def create_tax_rate(
    data: TaxRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    tax_rate = TaxRate(**data.model_dump())
    db.add(tax_rate)

    if data.is_default:
        db.query(TaxRate).filter(TaxRate.is_default == True).update({"is_default": False})  # noqa: E712

    db.commit()
    db.refresh(tax_rate)
    return tax_rate


@router.get("/tax-rates", response_model=list[TaxRateResponse])
async def list_tax_rates(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(TaxRate)
    if active_only:
        q = q.filter(TaxRate.is_active == True)  # noqa: E712
    return q.order_by(TaxRate.name).all()


@router.put("/tax-rates/{tax_rate_id}/set-default", response_model=TaxRateResponse)
async def set_default_tax_rate(
    tax_rate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    tax_rate = db.query(TaxRate).filter(TaxRate.id == tax_rate_id).first()
    if not tax_rate:
        raise HTTPException(status_code=404, detail="Tax rate not found")

    db.query(TaxRate).filter(TaxRate.is_default == True).update({"is_default": False})  # noqa: E712
    tax_rate.is_default = True
    db.commit()
    db.refresh(tax_rate)
    return tax_rate


# ── PAYMENT MODE MASTER ─────────────────────────────────────────────

@router.post("/payment-modes", response_model=PaymentModeMasterResponse, status_code=201)
async def create_payment_mode(
    data: PaymentModeMasterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    existing = db.query(PaymentModeMaster).filter(PaymentModeMaster.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="This payment mode code already exists")
    mode = PaymentModeMaster(**data.model_dump())
    db.add(mode)
    db.commit()
    db.refresh(mode)
    return mode


@router.get("/payment-modes", response_model=list[PaymentModeMasterResponse])
async def list_payment_modes(
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(PaymentModeMaster)
    if enabled_only:
        q = q.filter(PaymentModeMaster.is_enabled == True)  # noqa: E712
    return q.order_by(PaymentModeMaster.display_name).all()


@router.put("/payment-modes/{mode_id}/toggle", response_model=PaymentModeMasterResponse)
async def toggle_payment_mode(
    mode_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    mode = db.query(PaymentModeMaster).filter(PaymentModeMaster.id == mode_id).first()
    if not mode:
        raise HTTPException(status_code=404, detail="Payment mode not found")
    mode.is_enabled = not mode.is_enabled
    db.commit()
    db.refresh(mode)
    return mode


# ── UNIFIED STAFF DIRECTORY (item 171) ──────────────────
@router.get("/unified-staff", response_model=list[UnifiedStaffEntry])
async def list_unified_staff(department_id: Optional[int] = Query(None),
                              doctors_only: bool = Query(False),
                              db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    """
    One row per person across both DoctorProfile and StaffProfile, joined
    by User -> optionally DoctorProfile.staff_profile_id where linked.
    Built as a query-time join, not a materialized table, so it can never
    drift out of sync with the two source tables it reads from.
    """
    entries: dict[int, UnifiedStaffEntry] = {}   # keyed by user_id

    doctors = db.query(DoctorProfile).all()
    for d in doctors:
        user = db.query(User).filter(User.id == d.user_id).first()
        if not user:
            continue
        linked_staff = db.query(StaffProfile).filter(StaffProfile.id == d.staff_profile_id).first() if d.staff_profile_id else None
        entries[user.id] = UnifiedStaffEntry(
            user_id=user.id, full_name=user.full_name, email=user.email, phone=user.phone,
            is_doctor=True, doctor_profile_id=d.id, specialization=d.specialization,
            registration_number=d.registration_number,
            is_staff=linked_staff is not None,
            staff_profile_id=linked_staff.id if linked_staff else None,
            employee_code=linked_staff.employee_code if linked_staff else None,
            department_id=linked_staff.department_id if linked_staff else None,
            designation_id=linked_staff.designation_id if linked_staff else None,
            date_of_joining=linked_staff.date_of_joining if linked_staff else None,
            is_active=linked_staff.is_active if linked_staff else d.is_available,
        )

    if not doctors_only:
        staff = db.query(StaffProfile).all()
        for s in staff:
            user = db.query(User).filter(User.id == s.user_id).first()
            if not user or user.id in entries:
                continue   # already covered via a linked DoctorProfile above
            if department_id and s.department_id != department_id:
                continue
            entries[user.id] = UnifiedStaffEntry(
                user_id=user.id, full_name=user.full_name, email=user.email, phone=user.phone,
                is_doctor=False, is_staff=True, staff_profile_id=s.id,
                employee_code=s.employee_code, department_id=s.department_id,
                designation_id=s.designation_id, date_of_joining=s.date_of_joining,
                is_active=s.is_active,
            )

    results = list(entries.values())
    if department_id:
        results = [e for e in results if e.department_id == department_id]
    if doctors_only:
        results = [e for e in results if e.is_doctor]
    return results


@router.post("/unified-staff/link", response_model=UnifiedStaffEntry)
async def link_doctor_to_staff(data: LinkDoctorToStaffRequest, db: Session = Depends(get_db),
                                current_user: User = Depends(require_roles(UserRole.ADMIN))):
    """Links an existing DoctorProfile to an existing StaffProfile - for a
    doctor who's on the hospital's employment payroll, so their leave/
    attendance/salary-structure data (already keyed by staff_profile_id)
    shows up alongside their clinical profile in the unified view above."""
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == data.doctor_profile_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    staff = db.query(StaffProfile).filter(StaffProfile.id == data.staff_profile_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff profile not found")
    if doctor.user_id != staff.user_id:
        raise HTTPException(status_code=400,
                             detail="This doctor profile and staff profile belong to different user accounts")

    doctor.staff_profile_id = staff.id
    db.commit()

    user = db.query(User).filter(User.id == doctor.user_id).first()
    return UnifiedStaffEntry(
        user_id=user.id, full_name=user.full_name, email=user.email, phone=user.phone,
        is_doctor=True, doctor_profile_id=doctor.id, specialization=doctor.specialization,
        registration_number=doctor.registration_number,
        is_staff=True, staff_profile_id=staff.id, employee_code=staff.employee_code,
        department_id=staff.department_id, designation_id=staff.designation_id,
        date_of_joining=staff.date_of_joining, is_active=staff.is_active,
    )
