from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, timedelta, datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.blood_bank import BloodDonor, BloodStock, BloodDonation, BloodRequest, BloodGroup, BloodRequestStatus, DonorStatus
from app.models.patient import Patient

router = APIRouter(tags=["Blood Bank"])


def ensure_stock_rows(db: Session):
    for group in BloodGroup:
        if not db.query(BloodStock).filter(BloodStock.blood_group == group).first():
            db.add(BloodStock(blood_group=group, units_available=0, units_reserved=0, minimum_stock=2))
    db.commit()


@router.get("/blood-bank/dashboard")
async def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ensure_stock_rows(db)
    stock = db.query(BloodStock).all()
    return {
        "stock": [{"blood_group": s.blood_group, "units_available": s.units_available, "units_reserved": s.units_reserved, "minimum_stock": s.minimum_stock, "is_critical": s.units_available <= s.minimum_stock} for s in stock],
        "total_donors": db.query(BloodDonor).filter(BloodDonor.is_active == True).count(),
        "pending_requests": db.query(BloodRequest).filter(BloodRequest.status == BloodRequestStatus.PENDING).count(),
        "critical_groups": sum(1 for s in stock if s.units_available <= s.minimum_stock),
    }


@router.post("/blood-bank/donors", status_code=201)
async def add_donor(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(BloodDonor).count()
    donor = BloodDonor(donor_id=f"DON{count+1:04d}", name=data["name"], blood_group=data["blood_group"], age=data.get("age"), gender=data.get("gender"), phone=data.get("phone"), email=data.get("email"))
    db.add(donor); db.commit(); db.refresh(donor)
    return {"id": donor.id, "donor_id": donor.donor_id, "name": donor.name}


@router.get("/blood-bank/donors")
async def list_donors(blood_group: Optional[str] = Query(None), search: Optional[str] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(BloodDonor).filter(BloodDonor.is_active == True)
    if blood_group: q = q.filter(BloodDonor.blood_group == blood_group)
    if search: q = q.filter(BloodDonor.name.ilike(f"%{search}%"))
    return [{"id": d.id, "donor_id": d.donor_id, "name": d.name, "blood_group": d.blood_group, "age": d.age, "gender": d.gender, "phone": d.phone, "last_donation_date": d.last_donation_date, "total_donations": d.total_donations, "status": d.status} for d in q.order_by(BloodDonor.created_at.desc()).all()]


@router.post("/blood-bank/donations", status_code=201)
async def record_donation(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donor = db.query(BloodDonor).filter(BloodDonor.id == data["donor_id"]).first()
    if not donor: raise HTTPException(status_code=404, detail="Donor not found")
    donation_date = date.fromisoformat(data["donation_date"]) if isinstance(data["donation_date"], str) else data["donation_date"]
    expiry_date = donation_date + timedelta(days=35)
    count = db.query(BloodDonation).count()
    donation = BloodDonation(donation_number=f"DON{count+1:05d}", donor_id=donor.id, blood_group=donor.blood_group, units=float(data.get("units", 1.0)), donation_date=donation_date, expiry_date=expiry_date, bag_number=data.get("bag_number", ""), collected_by=current_user.full_name)
    db.add(donation)
    ensure_stock_rows(db)
    stock = db.query(BloodStock).filter(BloodStock.blood_group == donor.blood_group).first()
    if stock: stock.units_available += float(data.get("units", 1.0))
    donor.last_donation_date = donation_date; donor.total_donations += 1
    db.commit(); db.refresh(donation)
    return {"id": donation.id, "donation_number": donation.donation_number, "expiry_date": str(expiry_date)}


@router.get("/blood-bank/donations")
async def list_donations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    donations = db.query(BloodDonation).filter(BloodDonation.is_active == True).order_by(BloodDonation.donation_date.desc()).limit(100).all()
    result = []
    for d in donations:
        donor = db.query(BloodDonor).filter(BloodDonor.id == d.donor_id).first()
        result.append({"id": d.id, "donation_number": d.donation_number, "donor_name": donor.name if donor else "—", "blood_group": d.blood_group, "units": d.units, "donation_date": str(d.donation_date), "expiry_date": str(d.expiry_date), "bag_number": d.bag_number, "is_expired": d.expiry_date < date.today()})
    return result


@router.post("/blood-bank/requests", status_code=201)
async def create_request(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(BloodRequest).count()
    req = BloodRequest(request_number=f"BBR{count+1:05d}", patient_id=data.get("patient_id"), blood_group=data["blood_group"], units_requested=float(data["units_requested"]), reason=data.get("reason", ""), doctor_name=data.get("doctor_name", ""), priority=data.get("priority", "routine"))
    db.add(req); db.commit(); db.refresh(req)
    return {"id": req.id, "request_number": req.request_number}


@router.get("/blood-bank/requests")
async def list_requests(status: Optional[str] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(BloodRequest)
    if status: q = q.filter(BloodRequest.status == status)
    requests = q.order_by(BloodRequest.requested_date.desc()).limit(100).all()
    result = []
    for r in requests:
        patient = db.query(Patient).filter(Patient.id == r.patient_id).first() if r.patient_id else None
        result.append({"id": r.id, "request_number": r.request_number, "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "—", "blood_group": r.blood_group, "units_requested": r.units_requested, "units_issued": r.units_issued, "reason": r.reason, "doctor_name": r.doctor_name, "priority": r.priority, "status": r.status, "requested_date": r.requested_date})
    return result


@router.put("/blood-bank/requests/{request_id}/issue")
async def issue_blood(request_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not req: raise HTTPException(status_code=404, detail="Request not found")
    ensure_stock_rows(db)
    stock = db.query(BloodStock).filter(BloodStock.blood_group == req.blood_group).first()
    units = float(data.get("units", req.units_requested))
    if not stock or stock.units_available < units:
        raise HTTPException(status_code=400, detail=f"Insufficient stock. Available: {stock.units_available if stock else 0}")
    stock.units_available -= units; req.units_issued = units; req.status = BloodRequestStatus.ISSUED; req.issued_date = datetime.utcnow()
    db.commit()
    return {"message": f"{units} unit(s) issued"}


@router.put("/blood-bank/requests/{request_id}/reject")
async def reject_request(request_id: int, data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if not req: raise HTTPException(status_code=404, detail="Request not found")
    req.status = BloodRequestStatus.REJECTED; req.notes = data.get("reason", "")
    db.commit()
    return {"message": "Rejected"}
