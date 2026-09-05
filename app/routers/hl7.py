from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.patient import Patient
from app.models.ipd import IPDAdmission, Ward
from app.models.lab import LabOrderItem, LabOrder, LabTest
from app.models.user import User
from app.services import hl7_generator as hl7

router = APIRouter(prefix="/hl7", tags=["HL7 v2 (Interoperability)"])


def _ward_bed_labels(db: Session, admission: IPDAdmission):
    ward = db.query(Ward).filter(Ward.id == admission.ward_id).first() if admission.ward_id else None
    return (ward.name if ward else ""), (str(admission.bed_id) if admission.bed_id else "")


@router.get("/adt/admission/{admission_id}", response_class=PlainTextResponse)
async def generate_adt_a01(admission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    admission = db.query(IPDAdmission).filter(IPDAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    patient = db.query(Patient).filter(Patient.id == admission.patient_id).first()
    ward_name, bed_label = _ward_bed_labels(db, admission)
    return hl7.build_adt_a01(patient, admission, ward_name, bed_label)


@router.get("/adt/discharge/{admission_id}", response_class=PlainTextResponse)
async def generate_adt_a03(admission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    admission = db.query(IPDAdmission).filter(IPDAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    patient = db.query(Patient).filter(Patient.id == admission.patient_id).first()
    ward_name, bed_label = _ward_bed_labels(db, admission)
    return hl7.build_adt_a03(patient, admission, ward_name, bed_label)


@router.get("/adt/update/{admission_id}", response_class=PlainTextResponse)
async def generate_adt_a08(admission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    admission = db.query(IPDAdmission).filter(IPDAdmission.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    patient = db.query(Patient).filter(Patient.id == admission.patient_id).first()
    ward_name, bed_label = _ward_bed_labels(db, admission)
    return hl7.build_adt_a08(patient, admission, ward_name, bed_label)


@router.get("/oru/lab-result/{lab_order_item_id}", response_class=PlainTextResponse)
async def generate_oru_r01(lab_order_item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(LabOrderItem).filter(LabOrderItem.id == lab_order_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Lab result item not found")
    order = db.query(LabOrder).filter(LabOrder.id == item.order_id).first()
    test = db.query(LabTest).filter(LabTest.id == item.test_id).first()
    patient = db.query(Patient).filter(Patient.id == order.patient_id).first() if order else None
    if not patient:
        raise HTTPException(status_code=404, detail="Could not resolve patient for this result")
    return hl7.build_oru_r01(patient, order, test, item)
