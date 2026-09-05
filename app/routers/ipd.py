from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.ipd import Ward, Bed, IPDAdmission, NursingNote, DailyProgressNote, VitalChart, BedStatus, IPDStatus, WardType
from app.models.user import User
from app.schemas.ipd import (
    WardCreate, WardResponse, BedCreate, BedResponse,
    IPDAdmissionCreate, IPDAdmissionUpdate, IPDAdmissionResponse,
    NursingNoteCreate, NursingNoteResponse,
    ProgressNoteCreate, ProgressNoteResponse,
    VitalChartCreate, VitalChartResponse
)

router = APIRouter(prefix="/ipd", tags=["IPD"])


# ── WARDS ─────────────────────────────────────────────
@router.post("/wards", response_model=WardResponse, status_code=201)
async def create_ward(data: WardCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    ward = Ward(**data.model_dump(), available_beds=data.total_beds)
    db.add(ward)
    db.commit()
    db.refresh(ward)

    # Auto-create the ward's beds (BED-NUMBER must be globally unique, so
    # prefix with the ward id, e.g. ward #3 with 10 beds -> W3-01..W3-10)
    icu_types = {WardType.ICU, WardType.NICU, WardType.HDU}
    default_bed_type = "icu" if ward.ward_type in icu_types else "standard"
    for i in range(1, ward.total_beds + 1):
        db.add(Bed(
            ward_id=ward.id,
            bed_number=f"W{ward.id}-{i:02d}",
            bed_type=default_bed_type,
            status=BedStatus.AVAILABLE,
            is_active=True,
        ))
    db.commit()
    db.refresh(ward)
    return ward


@router.get("/wards", response_model=list[WardResponse])
async def list_wards(db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    return db.query(Ward).filter(Ward.is_active == True).all()


@router.get("/wards/{ward_id}/beds", response_model=list[BedResponse])
async def get_ward_beds(ward_id: int, status: Optional[BedStatus] = None,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    query = db.query(Bed).filter(Bed.ward_id == ward_id, Bed.is_active == True)
    if status:
        query = query.filter(Bed.status == status)
    return query.all()


@router.post("/beds", response_model=BedResponse, status_code=201)
async def create_bed(data: BedCreate, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    bed = Bed(**data.model_dump())
    db.add(bed)
    db.commit()
    db.refresh(bed)
    return bed


@router.get("/beds/available")
async def get_available_beds(ward_id: Optional[int] = None,
                              db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    query = db.query(Bed).filter(Bed.status == BedStatus.AVAILABLE, Bed.is_active == True)
    if ward_id:
        query = query.filter(Bed.ward_id == ward_id)
    beds = query.all()
    return [{"id": b.id, "bed_number": b.bed_number, "ward_id": b.ward_id,
             "ward_name": b.ward.name if b.ward else None,
             "bed_type": b.bed_type, "status": b.status} for b in beds]


# ── ADMISSIONS ────────────────────────────────────────
@router.post("/admissions", response_model=IPDAdmissionResponse, status_code=201)
async def admit_patient(data: IPDAdmissionCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    from sqlalchemy.exc import IntegrityError

    admission_data = data.model_dump()
    attempt_base = next_sequence_number(db, IPDAdmission)
    admission = None
    last_error = None
    for i in range(MAX_RETRIES):
        admission = IPDAdmission(
            **admission_data,
            admission_number=f"IPD{attempt_base + i:07d}",
            admitted_by=current_user.id
        )
        db.add(admission)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            admission = None
    if last_error:
        raise last_error

    # Mark bed occupied
    if data.bed_id:
        bed = db.query(Bed).filter(Bed.id == data.bed_id).first()
        if bed:
            if bed.status != BedStatus.AVAILABLE:
                raise HTTPException(status_code=400, detail="Bed is not available")
            bed.status = BedStatus.OCCUPIED
            # Update ward available_beds count
            if bed.ward:
                bed.ward.available_beds = max(0, bed.ward.available_beds - 1)

    db.commit()
    db.refresh(admission)
    return admission


@router.get("/admissions", response_model=list[IPDAdmissionResponse])
async def list_admissions(status: Optional[IPDStatus] = Query(None),
                          patient_id: Optional[int] = Query(None),
                          ward_id: Optional[int] = Query(None),
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    query = db.query(IPDAdmission)
    if status:
        query = query.filter(IPDAdmission.status == status)
    if patient_id:
        query = query.filter(IPDAdmission.patient_id == patient_id)
    if ward_id:
        query = query.filter(IPDAdmission.ward_id == ward_id)
    return query.order_by(IPDAdmission.admission_date.desc()).limit(100).all()


@router.get("/admissions/active")
async def get_active_admissions(db: Session = Depends(get_db),
                                 current_user: User = Depends(get_current_user)):
    admissions = db.query(IPDAdmission).filter(
        IPDAdmission.status == IPDStatus.ADMITTED).all()
    return [{
        "id": a.id, "admission_number": a.admission_number,
        "patient_name": f"{a.patient.first_name} {a.patient.last_name}" if a.patient else None,
        "patient_uhid": a.patient.uhid if a.patient else None,
        "bed_number": a.bed.bed_number if a.bed else None,
        "ward_name": a.ward.name if a.ward else None,
        "admission_date": a.admission_date,
        "diagnosis": a.diagnosis_at_admission,
        "days_admitted": (datetime.utcnow() - a.admission_date.replace(tzinfo=None)).days if a.admission_date else 0
    } for a in admissions]


@router.get("/admissions/{admission_id}", response_model=IPDAdmissionResponse)
async def get_admission(admission_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    a = db.query(IPDAdmission).filter(IPDAdmission.id == admission_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Admission not found")
    return a


@router.put("/admissions/{admission_id}", response_model=IPDAdmissionResponse)
async def update_admission(admission_id: int, data: IPDAdmissionUpdate,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    admission = db.query(IPDAdmission).filter(IPDAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")

    # Handle discharge - free up bed (goes to CLEANING first, not
    # directly AVAILABLE - a discharged bed must be cleaned before the
    # next patient, tracked via the Housekeeping module)
    if data.status in [IPDStatus.DISCHARGED, IPDStatus.TRANSFERRED, IPDStatus.EXPIRED, IPDStatus.LAMA]:
        if admission.bed_id and admission.status == IPDStatus.ADMITTED:
            bed = db.query(Bed).filter(Bed.id == admission.bed_id).first()
            if bed:
                bed.status = BedStatus.CLEANING
        admission.discharge_date = datetime.utcnow()

    # Handle bed transfer
    if data.bed_id and data.bed_id != admission.bed_id:
        new_bed = db.query(Bed).filter(Bed.id == data.bed_id).first()
        if new_bed and new_bed.status != BedStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail="Target bed not available")
        # Free old bed
        if admission.bed_id:
            old_bed = db.query(Bed).filter(Bed.id == admission.bed_id).first()
            if old_bed:
                old_bed.status = BedStatus.AVAILABLE
                if old_bed.ward:
                    old_bed.ward.available_beds += 1
        # Occupy new bed
        if new_bed:
            new_bed.status = BedStatus.OCCUPIED
            if new_bed.ward:
                new_bed.ward.available_beds = max(0, new_bed.ward.available_beds - 1)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(admission, field, value)
    db.commit()
    db.refresh(admission)
    return admission


# ── NURSING NOTES ─────────────────────────────────────
@router.post("/nursing-notes", response_model=NursingNoteResponse, status_code=201)
async def add_nursing_note(data: NursingNoteCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    note = NursingNote(**data.model_dump(), nurse_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/nursing-notes/{admission_id}", response_model=list[NursingNoteResponse])
async def get_nursing_notes(admission_id: int, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    return db.query(NursingNote).filter(
        NursingNote.admission_id == admission_id
    ).order_by(NursingNote.created_at.desc()).all()


# ── PROGRESS NOTES ────────────────────────────────────
@router.post("/progress-notes", response_model=ProgressNoteResponse, status_code=201)
async def add_progress_note(data: ProgressNoteCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    from app.models.doctor import DoctorProfile
    doctor = db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=403, detail="Only doctors can add progress notes")
    note = DailyProgressNote(**data.model_dump(), doctor_id=doctor.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/progress-notes/{admission_id}", response_model=list[ProgressNoteResponse])
async def get_progress_notes(admission_id: int, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    return db.query(DailyProgressNote).filter(
        DailyProgressNote.admission_id == admission_id
    ).order_by(DailyProgressNote.created_at.desc()).all()


# ── VITALS ────────────────────────────────────────────
@router.post("/vitals", response_model=VitalChartResponse, status_code=201)
async def record_vitals(data: VitalChartCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    vital = VitalChart(**data.model_dump(), recorded_by=current_user.id)
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return vital


@router.get("/vitals/{admission_id}", response_model=list[VitalChartResponse])
async def get_vitals(admission_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    return db.query(VitalChart).filter(
        VitalChart.admission_id == admission_id
    ).order_by(VitalChart.recorded_at.desc()).all()


# ── DASHBOARD ─────────────────────────────────────────
@router.get("/dashboard/stats")
async def ipd_dashboard(db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    total_beds = db.query(Bed).filter(Bed.is_active == True).count()
    occupied = db.query(Bed).filter(Bed.status == BedStatus.OCCUPIED).count()
    available = db.query(Bed).filter(Bed.status == BedStatus.AVAILABLE).count()
    current_admissions = db.query(IPDAdmission).filter(
        IPDAdmission.status == IPDStatus.ADMITTED).count()
    return {
        "total_beds": total_beds, "occupied_beds": occupied,
        "available_beds": available, "current_admissions": current_admissions,
        "occupancy_rate": round((occupied / total_beds * 100) if total_beds > 0 else 0, 1)
    }




@router.post("/admissions/{admission_id}/transfer-bed")
async def transfer_bed(
    admission_id: int, data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    admission = db.query(IPDAdmission).filter(IPDAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    new_bed_id = data.get("bed_id")
    new_ward_id = data.get("ward_id")
    if admission.bed_id:
        old_bed = db.query(Bed).filter(Bed.id == admission.bed_id).first()
        if old_bed:
            old_bed.status = BedStatus.AVAILABLE
            old_ward = db.query(Ward).filter(Ward.id == admission.ward_id).first()
            if old_ward:
                old_ward.available_beds = min(old_ward.total_beds, (old_ward.available_beds or 0) + 1)
    if new_bed_id:
        new_bed = db.query(Bed).filter(Bed.id == new_bed_id).first()
        if not new_bed:
            raise HTTPException(status_code=404, detail="Bed not found")
        if new_bed.status != BedStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail="Bed not available")
        new_bed.status = BedStatus.OCCUPIED
        admission.bed_id = new_bed_id
        if new_ward_id:
            new_ward = db.query(Ward).filter(Ward.id == new_ward_id).first()
            if new_ward:
                new_ward.available_beds = max(0, (new_ward.available_beds or 0) - 1)
    if new_ward_id:
        admission.ward_id = new_ward_id
    db.commit()
    return {"message": "Patient transferred successfully"}
