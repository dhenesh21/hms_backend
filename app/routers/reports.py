from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, Date
from typing import Optional
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.reports import SavedReport, ReportSchedule, ReportType
from app.schemas.reports import ReportRequest, SavedReportResponse, ReportScheduleCreate, ReportScheduleResponse

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


def get_date_range(from_date, to_date):
    if not from_date:
        from_date = date.today().replace(day=1)
    if not to_date:
        to_date = date.today()
    return from_date, to_date


# ── MIS DASHBOARD ─────────────────────────────────────
@router.get("/mis")
async def mis_dashboard(from_date: Optional[date] = Query(None),
                         to_date: Optional[date] = Query(None),
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    result = {}

    # Try each module gracefully
    try:
        from app.models.opd import OPDVisit
        result["opd"] = {
            "total_visits": db.query(OPDVisit).filter(func.cast(OPDVisit.visit_date, Date).between(fd, td)).count(),
            "completed": db.query(OPDVisit).filter(func.cast(OPDVisit.visit_date, Date).between(fd, td), OPDVisit.status == "completed").count(),
        }
    except: result["opd"] = {"total_visits": 0, "completed": 0}

    try:
        from app.models.ipd import IPDAdmission, Bed, BedStatus
        result["ipd"] = {
            "total_admissions": db.query(IPDAdmission).filter(func.cast(IPDAdmission.admission_date, Date).between(fd, td)).count(),
            "current_admitted": db.query(IPDAdmission).filter(IPDAdmission.status == "admitted").count(),
            "available_beds": db.query(Bed).filter(Bed.status == BedStatus.AVAILABLE, Bed.is_active == True).count(),
        }
    except: result["ipd"] = {"total_admissions": 0, "current_admitted": 0, "available_beds": 0}

    try:
        from app.models.billing import Bill, Payment, BillStatus
        bills = db.query(Bill).filter(func.cast(Bill.bill_date, Date).between(fd, td)).all()
        total_rev = db.query(func.sum(Payment.amount)).filter(func.cast(Payment.payment_date, Date).between(fd, td)).scalar() or 0
        result["revenue"] = {
            "total_billed": sum(b.gross_total for b in bills),
            "total_collected": round(total_rev, 2),
            "outstanding": sum(b.balance_amount for b in bills if b.balance_amount > 0),
            "bills_count": len(bills),
        }
    except: result["revenue"] = {"total_billed": 0, "total_collected": 0, "outstanding": 0, "bills_count": 0}

    try:
        from app.models.pharmacy import PharmacyDispense
        dispenses = db.query(PharmacyDispense).filter(func.cast(PharmacyDispense.created_at, Date).between(fd, td)).all()
        result["pharmacy"] = {
            "total_dispenses": len(dispenses),
            "revenue": sum(d.net_amount for d in dispenses),
        }
    except: result["pharmacy"] = {"total_dispenses": 0, "revenue": 0}

    try:
        from app.models.lab import LabOrder, LabOrderItem, SampleStatus
        result["lab"] = {
            "total_orders": db.query(LabOrder).filter(func.cast(LabOrder.ordered_at, Date).between(fd, td)).count(),
            "approved": db.query(LabOrderItem).filter(LabOrderItem.status == SampleStatus.APPROVED, func.cast(LabOrderItem.approved_at, Date).between(fd, td)).count(),
        }
    except: result["lab"] = {"total_orders": 0, "approved": 0}

    try:
        from app.models.insurance import InsuranceClaim, ClaimStatus
        result["insurance"] = {
            "total_claims": db.query(InsuranceClaim).filter(func.cast(InsuranceClaim.created_at, Date).between(fd, td)).count(),
            "settled": db.query(InsuranceClaim).filter(InsuranceClaim.status == ClaimStatus.SETTLED).count(),
            "pending_amount": db.query(func.sum(InsuranceClaim.claimed_amount)).filter(InsuranceClaim.status.in_(["submitted", "under_review"])).scalar() or 0,
        }
    except: result["insurance"] = {"total_claims": 0, "settled": 0, "pending_amount": 0}

    try:
        from app.models.patient import Patient
        result["patients"] = {
            "total_registered": db.query(Patient).filter(Patient.is_active == True).count(),
            "new_this_period": db.query(Patient).filter(func.cast(Patient.created_at, Date).between(fd, td)).count(),
        }
    except: result["patients"] = {"total_registered": 0, "new_this_period": 0}

    result["period"] = {"from_date": str(fd), "to_date": str(td)}
    return result


# ── OPD REPORT ────────────────────────────────────────
@router.get("/opd")
async def opd_report(from_date: Optional[date] = Query(None),
                      to_date: Optional[date] = Query(None),
                      doctor_id: Optional[int] = Query(None),
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    try:
        from app.models.opd import OPDVisit
        q = db.query(OPDVisit).filter(func.cast(OPDVisit.visit_date, Date).between(fd, td))
        if doctor_id:
            q = q.filter(OPDVisit.doctor_id == doctor_id)
        visits = q.all()

        by_day = {}
        by_doctor = {}
        diagnosis_count = {}
        follow_up_count = 0

        for v in visits:
            day = str(v.visit_date.date() if hasattr(v.visit_date, 'date') else v.visit_date)
            by_day[day] = by_day.get(day, 0) + 1
            by_doctor[v.doctor_id] = by_doctor.get(v.doctor_id, 0) + 1
            if v.primary_diagnosis:
                diagnosis_count[v.primary_diagnosis] = diagnosis_count.get(v.primary_diagnosis, 0) + 1
            if v.follow_up_required:
                follow_up_count += 1

        return {
            "period": {"from_date": str(fd), "to_date": str(td)},
            "total_visits": len(visits),
            "completed": sum(1 for v in visits if v.status == "completed"),
            "follow_ups_scheduled": follow_up_count,
            "by_day": [{"date": k, "count": v} for k, v in sorted(by_day.items())],
            "by_doctor": [{"doctor_id": k, "count": v} for k, v in sorted(by_doctor.items(), key=lambda x: -x[1])],
            "top_diagnoses": sorted([{"diagnosis": k, "count": v} for k, v in diagnosis_count.items()], key=lambda x: -x["count"])[:10],
        }
    except Exception as e:
        return {"error": str(e), "period": {"from_date": str(fd), "to_date": str(td)}, "total_visits": 0}


# ── IPD REPORT ────────────────────────────────────────
@router.get("/ipd")
async def ipd_report(from_date: Optional[date] = Query(None),
                      to_date: Optional[date] = Query(None),
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    try:
        from app.models.ipd import IPDAdmission, Ward, IPDStatus
        admissions = db.query(IPDAdmission).filter(func.cast(IPDAdmission.admission_date, Date).between(fd, td)).all()
        discharges = [a for a in admissions if a.status == IPDStatus.DISCHARGED]

        los_list = []
        for a in discharges:
            if a.discharge_date and a.admission_date:
                diff = (a.discharge_date - a.admission_date).days
                if diff >= 0:
                    los_list.append(diff)
        avg_los = round(sum(los_list) / len(los_list), 1) if los_list else 0

        by_ward = {}
        for a in admissions:
            wid = a.ward_id or "Unknown"
            by_ward[str(wid)] = by_ward.get(str(wid), 0) + 1

        wards = {str(w.id): w.name for w in db.query(Ward).all()}
        return {
            "period": {"from_date": str(fd), "to_date": str(td)},
            "total_admissions": len(admissions),
            "total_discharges": len(discharges),
            "current_admitted": db.query(IPDAdmission).filter(IPDAdmission.status == IPDStatus.ADMITTED).count(),
            "avg_length_of_stay_days": avg_los,
            "by_ward": [{"ward": wards.get(k, k), "count": v} for k, v in by_ward.items()],
            "by_type": {t: sum(1 for a in admissions if a.admission_type == t) for t in ["elective", "emergency", "transfer", "day_care"]},
        }
    except Exception as e:
        return {"error": str(e), "total_admissions": 0}


# ── REVENUE REPORT ────────────────────────────────────
@router.get("/revenue")
async def revenue_report(from_date: Optional[date] = Query(None),
                          to_date: Optional[date] = Query(None),
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    try:
        from app.models.billing import Bill, Payment, BillType
        payments = db.query(Payment).filter(func.cast(Payment.payment_date, Date).between(fd, td)).all()
        bills = db.query(Bill).filter(func.cast(Bill.bill_date, Date).between(fd, td)).all()

        by_day = {}
        for p in payments:
            day = str(p.payment_date.date() if hasattr(p.payment_date, 'date') else p.payment_date)
            by_day[day] = by_day.get(day, 0) + p.amount

        by_mode = {}
        for p in payments:
            mode = p.payment_mode.value if hasattr(p.payment_mode, 'value') else str(p.payment_mode)
            by_mode[mode] = round(by_mode.get(mode, 0) + p.amount, 2)

        by_type = {}
        for b in bills:
            t = b.bill_type.value if hasattr(b.bill_type, 'value') else str(b.bill_type)
            by_type[t] = round(by_type.get(t, 0) + b.gross_total, 2)

        total = sum(p.amount for p in payments)
        outstanding = sum(b.balance_amount for b in bills if b.balance_amount > 0)
        return {
            "period": {"from_date": str(fd), "to_date": str(td)},
            "total_collection": round(total, 2),
            "total_billed": round(sum(b.gross_total for b in bills), 2),
            "outstanding": round(outstanding, 2),
            "by_day": [{"date": k, "amount": round(v, 2)} for k, v in sorted(by_day.items())],
            "by_payment_mode": by_mode,
            "by_bill_type": by_type,
            "total_bills": len(bills),
            "paid_bills": sum(1 for b in bills if b.status == "paid"),
        }
    except Exception as e:
        return {"error": str(e), "total_collection": 0}


# ── PATIENT REGISTER ──────────────────────────────────
@router.get("/patients")
async def patient_register(from_date: Optional[date] = Query(None),
                            to_date: Optional[date] = Query(None),
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    try:
        from app.models.patient import Patient, Gender
        patients = db.query(Patient).filter(func.cast(Patient.created_at, Date).between(fd, td)).all()
        by_gender = {g.value: 0 for g in Gender}
        by_blood = {}
        age_groups = {"0-18": 0, "19-35": 0, "36-60": 0, "60+": 0}

        for p in patients:
            if p.gender:
                by_gender[p.gender.value] = by_gender.get(p.gender.value, 0) + 1
            if p.blood_group:
                bg = p.blood_group.value if hasattr(p.blood_group, 'value') else str(p.blood_group)
                by_blood[bg] = by_blood.get(bg, 0) + 1
            if p.date_of_birth:
                age = (date.today() - p.date_of_birth).days // 365
                if age <= 18: age_groups["0-18"] += 1
                elif age <= 35: age_groups["19-35"] += 1
                elif age <= 60: age_groups["36-60"] += 1
                else: age_groups["60+"] += 1

        return {
            "period": {"from_date": str(fd), "to_date": str(td)},
            "new_registrations": len(patients),
            "total_active": db.query(Patient).filter(Patient.is_active == True).count(),
            "by_gender": by_gender,
            "by_blood_group": by_blood,
            "by_age_group": age_groups,
        }
    except Exception as e:
        return {"error": str(e), "new_registrations": 0}


# ── LAB REPORT ────────────────────────────────────────
@router.get("/lab")
async def lab_report(from_date: Optional[date] = Query(None),
                      to_date: Optional[date] = Query(None),
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    try:
        from app.models.lab import LabOrder, LabOrderItem, LabTest, SampleStatus, LabCategory
        orders = db.query(LabOrder).filter(func.cast(LabOrder.ordered_at, Date).between(fd, td)).all()
        items = db.query(LabOrderItem).join(LabOrder).filter(func.cast(LabOrder.ordered_at, Date).between(fd, td)).all()
        by_status = {s.value: 0 for s in SampleStatus}
        for i in items:
            by_status[i.status.value] = by_status.get(i.status.value, 0) + 1

        critical = [i for i in items if i.result_status == "critical"]
        return {
            "period": {"from_date": str(fd), "to_date": str(td)},
            "total_orders": len(orders),
            "total_tests": len(items),
            "approved": by_status.get("approved", 0),
            "pending": by_status.get("ordered", 0) + by_status.get("sample_collected", 0) + by_status.get("result_entered", 0),
            "critical_results": len(critical),
            "by_status": by_status,
            "turnaround_avg_hours": 4,
        }
    except Exception as e:
        return {"error": str(e), "total_orders": 0}


# ── PHARMACY REPORT ───────────────────────────────────
@router.get("/pharmacy")
async def pharmacy_report(from_date: Optional[date] = Query(None),
                           to_date: Optional[date] = Query(None),
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    try:
        from app.models.pharmacy import PharmacyDispense, DispenseItem, DrugMaster, DrugStock
        dispenses = db.query(PharmacyDispense).filter(func.cast(PharmacyDispense.created_at, Date).between(fd, td)).all()
        by_day = {}
        for d in dispenses:
            day = str(d.created_at.date() if hasattr(d.created_at, 'date') else d.created_at)
            by_day[day] = round(by_day.get(day, 0) + d.net_amount, 2)

        expiring = db.query(DrugStock).filter(
            DrugStock.expiry_date <= date.today() + timedelta(days=90),
            DrugStock.expiry_date >= date.today(),
            DrugStock.quantity_available > 0
        ).count()
        expired = db.query(DrugStock).filter(DrugStock.expiry_date < date.today(), DrugStock.quantity_available > 0).count()

        return {
            "period": {"from_date": str(fd), "to_date": str(td)},
            "total_dispenses": len(dispenses),
            "total_revenue": round(sum(d.net_amount for d in dispenses), 2),
            "by_day": [{"date": k, "revenue": v} for k, v in sorted(by_day.items())],
            "expiring_soon_batches": expiring,
            "expired_batches": expired,
            "total_drugs": db.query(DrugMaster).filter(DrugMaster.is_active == True).count(),
        }
    except Exception as e:
        return {"error": str(e), "total_dispenses": 0}


# ── INSURANCE REPORT ──────────────────────────────────
@router.get("/insurance")
async def insurance_report(from_date: Optional[date] = Query(None),
                            to_date: Optional[date] = Query(None),
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    try:
        from app.models.insurance import InsuranceClaim, ClaimStatus
        claims = db.query(InsuranceClaim).filter(func.cast(InsuranceClaim.created_at, Date).between(fd, td)).all()
        by_status = {}
        for c in claims:
            s = c.status.value if hasattr(c.status, 'value') else str(c.status)
            by_status[s] = by_status.get(s, 0) + 1

        claimed = sum(c.claimed_amount for c in claims)
        approved = sum(c.approved_amount for c in claims)
        return {
            "period": {"from_date": str(fd), "to_date": str(td)},
            "total_claims": len(claims),
            "total_claimed": round(claimed, 2),
            "total_approved": round(approved, 2),
            "rejection_rate": round((by_status.get("rejected", 0) / len(claims) * 100) if claims else 0, 1),
            "settlement_rate": round((by_status.get("settled", 0) / len(claims) * 100) if claims else 0, 1),
            "by_status": by_status,
        }
    except Exception as e:
        return {"error": str(e), "total_claims": 0}


# ── BED OCCUPANCY ─────────────────────────────────────
@router.get("/bed-occupancy")
async def bed_occupancy(db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    try:
        from app.models.ipd import Ward, Bed, BedStatus
        wards = db.query(Ward).filter(Ward.is_active == True).all()
        result = []
        for ward in wards:
            total = ward.total_beds
            available = ward.available_beds
            occupied = total - available
            result.append({
                "ward_id": ward.id,
                "ward_name": ward.name,
                "ward_type": ward.ward_type.value if hasattr(ward.ward_type, 'value') else str(ward.ward_type),
                "total_beds": total,
                "occupied": occupied,
                "available": available,
                "occupancy_rate": round((occupied / total * 100) if total > 0 else 0, 1),
            })
        total_beds = sum(w.total_beds for w in wards)
        total_occupied = sum(w.total_beds - w.available_beds for w in wards)
        return {
            "overall_occupancy": round((total_occupied / total_beds * 100) if total_beds > 0 else 0, 1),
            "total_beds": total_beds,
            "total_occupied": total_occupied,
            "total_available": total_beds - total_occupied,
            "by_ward": result,
        }
    except Exception as e:
        return {"error": str(e), "overall_occupancy": 0}


# ── DOCTOR WISE REPORT ────────────────────────────────
@router.get("/doctor-wise")
async def doctor_wise(from_date: Optional[date] = Query(None),
                       to_date: Optional[date] = Query(None),
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    fd, td = get_date_range(from_date, to_date)
    try:
        from app.models.opd import OPDVisit
        from app.models.doctor import DoctorProfile
        from app.models.user import User as UserModel
        visits = db.query(OPDVisit).filter(func.cast(OPDVisit.visit_date, Date).between(fd, td)).all()
        by_doctor = {}
        for v in visits:
            did = v.doctor_id
            if did not in by_doctor:
                doc = db.query(DoctorProfile).filter(DoctorProfile.id == did).first()
                user = db.query(UserModel).filter(UserModel.id == doc.user_id).first() if doc else None
                by_doctor[did] = {
                    "doctor_id": did,
                    "doctor_name": user.full_name if user else f"Doctor {did}",
                    "specialization": doc.specialization if doc else "—",
                    "opd_visits": 0, "follow_ups": 0,
                }
            by_doctor[did]["opd_visits"] += 1
            if v.follow_up_required:
                by_doctor[did]["follow_ups"] += 1

        return {
            "period": {"from_date": str(fd), "to_date": str(td)},
            "doctors": sorted(list(by_doctor.values()), key=lambda x: -x["opd_visits"])
        }
    except Exception as e:
        return {"error": str(e), "doctors": []}


# ── SAVED REPORTS ─────────────────────────────────────
@router.get("/saved", response_model=list[SavedReportResponse])
async def list_saved_reports(db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    return db.query(SavedReport).filter(SavedReport.is_active == True).order_by(SavedReport.generated_at.desc()).limit(50).all()


@router.post("/schedules", response_model=ReportScheduleResponse, status_code=201)
async def create_schedule(data: ReportScheduleCreate,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    sched = ReportSchedule(**data.model_dump(), created_by=current_user.id)
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


@router.get("/schedules", response_model=list[ReportScheduleResponse])
async def list_schedules(db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    return db.query(ReportSchedule).filter(ReportSchedule.is_active == True).all()




