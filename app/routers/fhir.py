from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.patient import Patient
from app.models.doctor import DoctorProfile
from app.models.user import User
from app.models.appointment import Appointment
from app.models.lab import LabOrderItem, LabOrder, LabTest
from app.models.emr import PatientAllergy, ChronicCondition
from app.models.insurance import InsuranceClaim, InsurancePolicy, InsuranceCompany
from app.models.billing import Payment
from app.models.fhir_audit import FHIRAccessLog
from app.services import fhir_mappers as fm

router = APIRouter(prefix="/fhir", tags=["FHIR (Interoperability)"])


def _log_access(db: Session, user: User, resource_type: str, resource_id=None, patient_id=None):
    db.add(FHIRAccessLog(accessed_by=user.id, resource_type=resource_type,
                          resource_id=str(resource_id) if resource_id else None, patient_id=patient_id))
    db.commit()


@router.get("/metadata")
async def capability_statement(request: Request):
    """No auth required — CapabilityStatement discovery is meant to be publicly readable per FHIR convention."""
    return fm.capability_statement(str(request.base_url))


@router.get("/Patient/{patient_id}")
async def get_patient(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    _log_access(db, current_user, "Patient", patient_id, patient_id)
    return fm.patient_to_fhir(patient)


@router.get("/Patient")
async def search_patients(identifier: Optional[str] = None, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    """Search by identifier=<UHID> — the standard FHIR search pattern for a business identifier."""
    q = db.query(Patient)
    if identifier:
        q = q.filter(Patient.uhid == identifier)
    patients = q.limit(50).all()
    _log_access(db, current_user, "Patient")
    return {"resourceType": "Bundle", "type": "searchset", "total": len(patients),
            "entry": [{"resource": fm.patient_to_fhir(p)} for p in patients]}


@router.get("/Practitioner/{doctor_id}")
async def get_practitioner(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    user = db.query(User).filter(User.id == doc.user_id).first()
    _log_access(db, current_user, "Practitioner", doctor_id)
    return fm.practitioner_to_fhir(doc, user)


@router.get("/Encounter/{appointment_id}")
async def get_encounter(appointment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Encounter not found")
    _log_access(db, current_user, "Encounter", appointment_id, appt.patient_id)
    return fm.appointment_to_fhir_encounter(appt)


@router.get("/Encounter")
async def search_encounters(patient: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    appts = db.query(Appointment).filter(Appointment.patient_id == patient).limit(50).all()
    _log_access(db, current_user, "Encounter", patient_id=patient)
    return {"resourceType": "Bundle", "type": "searchset", "total": len(appts),
            "entry": [{"resource": fm.appointment_to_fhir_encounter(a)} for a in appts]}


@router.get("/Observation")
async def search_observations(patient: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(LabOrderItem, LabTest, LabOrder)
        .join(LabTest, LabOrderItem.test_id == LabTest.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .filter(LabOrder.patient_id == patient)
        .limit(100).all()
    )
    _log_access(db, current_user, "Observation", patient_id=patient)
    return {"resourceType": "Bundle", "type": "searchset", "total": len(rows),
            "entry": [{"resource": fm.lab_result_to_fhir_observation(item, test, order)} for item, test, order in rows]}


@router.get("/AllergyIntolerance")
async def search_allergies(patient: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    allergies = db.query(PatientAllergy).filter(PatientAllergy.patient_id == patient).all()
    _log_access(db, current_user, "AllergyIntolerance", patient_id=patient)
    return {"resourceType": "Bundle", "type": "searchset", "total": len(allergies),
            "entry": [{"resource": fm.allergy_to_fhir(a)} for a in allergies]}


@router.get("/Condition")
async def search_conditions(patient: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conditions = db.query(ChronicCondition).filter(ChronicCondition.patient_id == patient).all()
    _log_access(db, current_user, "Condition", patient_id=patient)
    return {"resourceType": "Bundle", "type": "searchset", "total": len(conditions),
            "entry": [{"resource": fm.condition_to_fhir(c)} for c in conditions]}


@router.get("/Claim/{claim_id}")
async def get_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Item 251 as the international-standard FHIR Claim shape — see fhir_mappers.claim_to_fhir docstring."""
    claim = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    policy = db.query(InsurancePolicy).filter(InsurancePolicy.id == claim.policy_id).first()
    company = db.query(InsuranceCompany).filter(InsuranceCompany.id == policy.company_id).first() if policy else None
    _log_access(db, current_user, "Claim", claim_id, claim.patient_id)
    return fm.claim_to_fhir(claim, company)


@router.get("/PaymentNotice/{payment_id}")
async def get_payment_notice(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Item 252 as the international-standard FHIR PaymentNotice shape — see fhir_mappers.payment_to_fhir_paymentnotice docstring."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    _log_access(db, current_user, "PaymentNotice", payment_id, payment.patient_id)
    return fm.payment_to_fhir_paymentnotice(payment)


@router.get("/Patient/{patient_id}/$everything")
async def patient_everything(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Item 257 (Health Information Exchange) via the internationally standard
    FHIR $everything operation — a single Bundle containing a patient's full
    exportable record (demographics + encounters + observations + allergies
    + conditions), which is exactly the mechanism real-world HIEs and
    patient-access APIs (e.g. US ONC Cures Act Patient Access API) use for
    record portability. This makes full-record export possible without
    joining any specific HIE network — a receiving system just needs to
    speak FHIR, not be a named partner. Joining an ACTUAL HIE network
    (authentication with that network, its specific trust framework) is
    still the Batch C "needs a specific target" situation; this is the
    data-shape layer that export would use regardless of which network.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    entries = [{"resource": fm.patient_to_fhir(patient)}]

    appts = db.query(Appointment).filter(Appointment.patient_id == patient_id).all()
    entries += [{"resource": fm.appointment_to_fhir_encounter(a)} for a in appts]

    lab_rows = (
        db.query(LabOrderItem, LabTest, LabOrder)
        .join(LabTest, LabOrderItem.test_id == LabTest.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .filter(LabOrder.patient_id == patient_id).all()
    )
    entries += [{"resource": fm.lab_result_to_fhir_observation(item, test, order)} for item, test, order in lab_rows]

    allergies = db.query(PatientAllergy).filter(PatientAllergy.patient_id == patient_id).all()
    entries += [{"resource": fm.allergy_to_fhir(a)} for a in allergies]

    conditions = db.query(ChronicCondition).filter(ChronicCondition.patient_id == patient_id).all()
    entries += [{"resource": fm.condition_to_fhir(c)} for c in conditions]

    _log_access(db, current_user, "Patient$everything", patient_id, patient_id)
    return {"resourceType": "Bundle", "type": "collection", "total": len(entries), "entry": entries}
