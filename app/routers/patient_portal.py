from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import (get_current_patient, get_current_user, get_password_hash,
                                verify_password, create_patient_access_token, require_roles)
from app.models.patient import Patient
from app.models.patient_portal import PatientAccount, PatientFeedback, PatientGrievance, GrievanceStatus
from app.models.appointment import Appointment
from app.models.opd import OPDVisit
from app.models.ipd import IPDAdmission
from app.models.lab import LabOrder
from app.models.billing import Bill
from app.models.user import User, UserRole
from app.schemas.patient_portal import (
    PatientPortalRegister, PatientPortalLogin, PatientPortalTokenResponse, PatientPortalMeResponse,
    MyAppointmentResponse, MyOPDVisitResponse, MyIPDAdmissionResponse, MyLabOrderResponse, MyBillResponse,
    FeedbackCreate, FeedbackResponse, GrievanceCreate, GrievanceResponse, GrievanceStaffUpdate,
)

router = APIRouter(prefix="/patient-portal", tags=["Patient Portal"])


# ── AUTH ────────────────────────────────────────────────
@router.post("/register", response_model=PatientPortalTokenResponse, status_code=201)
async def register(data: PatientPortalRegister, db: Session = Depends(get_db)):
    """Self-service portal signup — verifies the person against an existing UHID
    (they must already be a registered hospital patient) before creating a login."""
    patient = db.query(Patient).filter(Patient.uhid == data.uhid).first()
    if not patient:
        raise HTTPException(status_code=404, detail="No patient found with this UHID")
    if patient.phone != data.phone:
        raise HTTPException(status_code=400, detail="Phone number does not match hospital records")
    if db.query(PatientAccount).filter(PatientAccount.patient_id == patient.id).first():
        raise HTTPException(status_code=400, detail="A portal account already exists for this patient")

    account = PatientAccount(
        patient_id=patient.id, phone=data.phone, email=data.email,
        hashed_password=get_password_hash(data.password),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    token = create_patient_access_token(account.id, patient.id)
    return PatientPortalTokenResponse(access_token=token, patient_id=patient.id)


@router.post("/login", response_model=PatientPortalTokenResponse)
async def login(data: PatientPortalLogin, db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    account = db.query(PatientAccount).filter(PatientAccount.phone == data.phone).first()
    if not account or not verify_password(data.password, account.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect phone or password")
    if not account.is_active:
        raise HTTPException(status_code=403, detail="This portal account has been deactivated")
    account.last_login = datetime.now(timezone.utc)
    db.commit()
    token = create_patient_access_token(account.id, account.patient_id)
    return PatientPortalTokenResponse(access_token=token, patient_id=account.patient_id)


@router.get("/me", response_model=PatientPortalMeResponse)
async def get_me(account: PatientAccount = Depends(get_current_patient)):
    return account


# ── SELF-SERVICE READ VIEWS (ownership enforced via account.patient_id) ──
@router.get("/my-appointments", response_model=List[MyAppointmentResponse])
async def my_appointments(account: PatientAccount = Depends(get_current_patient), db: Session = Depends(get_db)):
    return db.query(Appointment).filter(
        Appointment.patient_id == account.patient_id
    ).order_by(Appointment.appointment_date.desc()).all()


@router.get("/my-opd-visits", response_model=List[MyOPDVisitResponse])
async def my_opd_visits(account: PatientAccount = Depends(get_current_patient), db: Session = Depends(get_db)):
    return db.query(OPDVisit).filter(OPDVisit.patient_id == account.patient_id).all()


@router.get("/my-ipd-admissions", response_model=List[MyIPDAdmissionResponse])
async def my_ipd_admissions(account: PatientAccount = Depends(get_current_patient), db: Session = Depends(get_db)):
    return db.query(IPDAdmission).filter(IPDAdmission.patient_id == account.patient_id).all()


@router.get("/my-lab-orders", response_model=List[MyLabOrderResponse])
async def my_lab_orders(account: PatientAccount = Depends(get_current_patient), db: Session = Depends(get_db)):
    return db.query(LabOrder).filter(LabOrder.patient_id == account.patient_id).all()


@router.get("/my-bills", response_model=List[MyBillResponse])
async def my_bills(account: PatientAccount = Depends(get_current_patient), db: Session = Depends(get_db)):
    return db.query(Bill).filter(Bill.patient_id == account.patient_id).all()


# ── FEEDBACK (#198) ────────────────────────────────────
@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(data: FeedbackCreate, account: PatientAccount = Depends(get_current_patient),
                           db: Session = Depends(get_db)):
    if not (1 <= data.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    feedback = PatientFeedback(**data.model_dump(), patient_id=account.patient_id)
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


# ── GRIEVANCE (#199) — patient side ────────────────────
@router.post("/grievances", response_model=GrievanceResponse, status_code=201)
async def submit_grievance(data: GrievanceCreate, account: PatientAccount = Depends(get_current_patient),
                            db: Session = Depends(get_db)):
    grievance = PatientGrievance(**data.model_dump(), patient_id=account.patient_id)
    db.add(grievance)
    db.commit()
    db.refresh(grievance)
    return grievance


@router.get("/grievances", response_model=List[GrievanceResponse])
async def my_grievances(account: PatientAccount = Depends(get_current_patient), db: Session = Depends(get_db)):
    return db.query(PatientGrievance).filter(
        PatientGrievance.patient_id == account.patient_id
    ).order_by(PatientGrievance.created_at.desc()).all()


# ── GRIEVANCE — staff side (admin/reception triage) ────
@router.get("/admin/grievances", response_model=List[GrievanceResponse], tags=["Grievance (Staff)"])
async def list_all_grievances(status: Optional[GrievanceStatus] = None, db: Session = Depends(get_db),
                               current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST))):
    q = db.query(PatientGrievance)
    if status:
        q = q.filter(PatientGrievance.status == status)
    return q.order_by(PatientGrievance.created_at.desc()).all()


@router.patch("/admin/grievances/{grievance_id}", response_model=GrievanceResponse, tags=["Grievance (Staff)"])
async def update_grievance(grievance_id: int, data: GrievanceStaffUpdate, db: Session = Depends(get_db),
                            current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST))):
    from datetime import datetime, timezone
    grievance = db.query(PatientGrievance).filter(PatientGrievance.id == grievance_id).first()
    if not grievance:
        raise HTTPException(status_code=404, detail="Grievance not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(grievance, k, v)
    if data.status in (GrievanceStatus.RESOLVED, GrievanceStatus.CLOSED) and not grievance.resolved_at:
        grievance.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(grievance)
    return grievance
