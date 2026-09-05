from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import datetime, date, timedelta
import calendar
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.id_generator import next_sequence_number, MAX_RETRIES
from app.models.hr import (Department, Designation, StaffProfile, Attendance,
                             LeaveApplication, LeaveBalance, Holiday, Payroll,
                             SalaryStructure, SalaryComponent, ShiftAssignment,
                             AttendanceStatus, LeaveStatus, LeaveType, PayrollStatus)
from app.models.user import User
from app.schemas.hr import (
    DepartmentCreate, DepartmentResponse,
    DesignationCreate, DesignationResponse,
    StaffProfileCreate, StaffProfileUpdate, StaffProfileResponse, StaffListResponse,
    AttendanceCreate, AttendanceBulkCreate, AttendanceResponse,
    LeaveApplicationCreate, LeaveApprovalRequest, LeaveApplicationResponse,
    SalaryStructureCreate, SalaryStructureResponse,
    ShiftAssignmentCreate, ShiftAssignmentResponse,
    LeaveBalanceResponse, HolidayCreate, HolidayResponse,
    PayrollCreate, PayrollUpdate, PayrollResponse
)

router = APIRouter(prefix="/hr", tags=["HR & Payroll"])


# ── DEPARTMENTS ───────────────────────────────────────
@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(data: DepartmentCreate, db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    dept = Department(**data.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(branch_id: Optional[int] = None, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    q = db.query(Department).filter(Department.is_active == True)
    if branch_id:
        q = q.filter(Department.branch_id == branch_id)
    return q.all()


# ── DESIGNATIONS ──────────────────────────────────────
@router.post("/designations", response_model=DesignationResponse, status_code=201)
async def create_designation(data: DesignationCreate, db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    desig = Designation(**data.model_dump())
    db.add(desig)
    db.commit()
    db.refresh(desig)
    return desig


@router.get("/designations", response_model=list[DesignationResponse])
async def list_designations(department_id: Optional[int] = None,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    q = db.query(Designation).filter(Designation.is_active == True)
    if department_id:
        q = q.filter(Designation.department_id == department_id)
    return q.all()


# ── STAFF ─────────────────────────────────────────────
@router.post("/staff", response_model=StaffProfileResponse, status_code=201)
async def create_staff(data: StaffProfileCreate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    if db.query(StaffProfile).filter(StaffProfile.employee_code == data.employee_code).first():
        raise HTTPException(status_code=400, detail="Employee code already exists")
    staff = StaffProfile(**data.model_dump())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    # Initialize leave balances for current year
    _init_leave_balances(db, staff.id)
    return staff


def _init_leave_balances(db: Session, staff_id: int):
    year = date.today().year
    defaults = {
        LeaveType.CASUAL: 12, LeaveType.SICK: 12,
        LeaveType.EARNED: 15, LeaveType.EMERGENCY: 3
    }
    for leave_type, days in defaults.items():
        existing = db.query(LeaveBalance).filter(
            LeaveBalance.staff_id == staff_id,
            LeaveBalance.year == year,
            LeaveBalance.leave_type == leave_type
        ).first()
        if not existing:
            lb = LeaveBalance(staff_id=staff_id, year=year, leave_type=leave_type,
                              total_days=days, balance_days=days)
            db.add(lb)
    db.commit()


@router.get("/staff", response_model=list[StaffListResponse])
async def list_staff(department_id: Optional[int] = None,
                     active_only: bool = True,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    q = db.query(StaffProfile)
    if active_only:
        q = q.filter(StaffProfile.is_active == True)
    if department_id:
        q = q.filter(StaffProfile.department_id == department_id)
    staff_list = q.all()
    result = []
    for s in staff_list:
        from app.models.user import User as UserModel
        user = db.query(UserModel).filter(UserModel.id == s.user_id).first()
        dept = db.query(Department).filter(Department.id == s.department_id).first() if s.department_id else None
        desig = db.query(Designation).filter(Designation.id == s.designation_id).first() if s.designation_id else None
        result.append(StaffListResponse(
            id=s.id, employee_code=s.employee_code,
            full_name=user.full_name if user else "Unknown",
            department_name=dept.name if dept else None,
            designation_title=desig.title if desig else None,
            employment_type=s.employment_type, shift=s.shift,
            date_of_joining=s.date_of_joining, is_active=s.is_active
        ))
    return result


@router.get("/staff/{staff_id}", response_model=StaffProfileResponse)
async def get_staff(staff_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    staff = db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.put("/staff/{staff_id}", response_model=StaffProfileResponse)
async def update_staff(staff_id: int, data: StaffProfileUpdate,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    staff = db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(staff, field, value)
    db.commit()
    db.refresh(staff)
    return staff


# ── ATTENDANCE ────────────────────────────────────────
@router.post("/attendance", response_model=AttendanceResponse, status_code=201)
async def mark_attendance(data: AttendanceCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    existing = db.query(Attendance).filter(
        Attendance.staff_id == data.staff_id,
        Attendance.date == data.date
    ).first()
    if existing:
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        existing.working_hours = _calc_hours(data.check_in, data.check_out)
        db.commit()
        db.refresh(existing)
        return existing

    att = Attendance(**data.model_dump(), marked_by=current_user.id)
    att.working_hours = _calc_hours(data.check_in, data.check_out)
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


def _calc_hours(check_in: Optional[str], check_out: Optional[str]) -> float:
    if not check_in or not check_out:
        return 0.0
    try:
        fmt = "%H:%M"
        ci = datetime.strptime(check_in, fmt)
        co = datetime.strptime(check_out, fmt)
        diff = (co - ci).seconds / 3600
        return round(max(0, diff), 2)
    except:
        return 0.0


@router.post("/attendance/bulk")
async def bulk_mark_attendance(data: AttendanceBulkCreate,
                                db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    count = 0
    for record in data.records:
        existing = db.query(Attendance).filter(
            Attendance.staff_id == record.staff_id,
            Attendance.date == data.date
        ).first()
        if existing:
            existing.status = record.status
        else:
            att = Attendance(staff_id=record.staff_id, date=data.date,
                             status=record.status, marked_by=current_user.id)
            db.add(att)
        count += 1
    db.commit()
    return {"message": f"{count} attendance records saved"}


@router.get("/attendance", response_model=list[AttendanceResponse])
async def get_attendance(staff_id: Optional[int] = None,
                          from_date: Optional[date] = None,
                          to_date: Optional[date] = None,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    q = db.query(Attendance)
    if staff_id:
        q = q.filter(Attendance.staff_id == staff_id)
    if from_date:
        q = q.filter(Attendance.date >= from_date)
    if to_date:
        q = q.filter(Attendance.date <= to_date)
    return q.order_by(Attendance.date.desc()).limit(500).all()


@router.get("/attendance/summary/{staff_id}")
async def attendance_summary(staff_id: int, month: int, year: int,
                              db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    records = db.query(Attendance).filter(
        Attendance.staff_id == staff_id,
        func.extract('month', Attendance.date) == month,
        func.extract('year', Attendance.date) == year
    ).all()
    summary = {s.value: 0 for s in AttendanceStatus}
    total_hours = 0.0
    for r in records:
        summary[r.status.value] = summary.get(r.status.value, 0) + 1
        total_hours += r.working_hours or 0
    return {"staff_id": staff_id, "month": month, "year": year,
            "summary": summary, "total_working_hours": round(total_hours, 2),
            "total_records": len(records)}


# ── LEAVES ────────────────────────────────────────────
@router.post("/leaves", response_model=LeaveApplicationResponse, status_code=201)
async def apply_leave(data: LeaveApplicationCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    delta = (data.to_date - data.from_date).days + 1
    total_days = 0.5 if data.half_day else float(delta)
    leave_data = data.model_dump()
    leave_data["total_days"] = total_days

    attempt_base = next_sequence_number(db, LeaveApplication)
    leave = None
    last_error = None
    for i in range(MAX_RETRIES):
        leave_data["application_number"] = f"LVE{attempt_base + i:06d}"
        leave = LeaveApplication(**leave_data)
        db.add(leave)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            leave = None
    if last_error:
        raise last_error

    # Update pending balance
    lb = db.query(LeaveBalance).filter(
        LeaveBalance.staff_id == data.staff_id,
        LeaveBalance.leave_type == data.leave_type,
        LeaveBalance.year == data.from_date.year
    ).first()
    if lb:
        lb.pending_days += total_days
        lb.balance_days -= total_days
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/leaves", response_model=list[LeaveApplicationResponse])
async def list_leaves(staff_id: Optional[int] = None,
                      status: Optional[LeaveStatus] = None,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    q = db.query(LeaveApplication)
    if staff_id:
        q = q.filter(LeaveApplication.staff_id == staff_id)
    if status:
        q = q.filter(LeaveApplication.status == status)
    return q.order_by(LeaveApplication.applied_at.desc()).limit(100).all()


@router.put("/leaves/{leave_id}/approve", response_model=LeaveApplicationResponse)
async def approve_leave(leave_id: int, data: LeaveApprovalRequest,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    leave = db.query(LeaveApplication).filter(LeaveApplication.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    leave.status = data.status
    leave.approved_by = current_user.id
    leave.approved_at = datetime.utcnow()
    leave.rejection_reason = data.rejection_reason
    lb = db.query(LeaveBalance).filter(
        LeaveBalance.staff_id == leave.staff_id,
        LeaveBalance.leave_type == leave.leave_type,
        LeaveBalance.year == leave.from_date.year
    ).first()
    if lb:
        lb.pending_days -= leave.total_days
        if data.status == LeaveStatus.APPROVED:
            lb.used_days += leave.total_days
        else:
            lb.balance_days += leave.total_days
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/leaves/balance/{staff_id}", response_model=list[LeaveBalanceResponse])
async def get_leave_balance(staff_id: int, year: Optional[int] = None,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    q = db.query(LeaveBalance).filter(LeaveBalance.staff_id == staff_id)
    if year:
        q = q.filter(LeaveBalance.year == year)
    return q.all()


# ── HOLIDAYS ──────────────────────────────────────────
@router.post("/holidays", response_model=HolidayResponse, status_code=201)
async def create_holiday(data: HolidayCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    holiday = Holiday(**data.model_dump())
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.get("/holidays", response_model=list[HolidayResponse])
async def list_holidays(year: Optional[int] = None,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    q = db.query(Holiday).filter(Holiday.is_active == True)
    if year:
        q = q.filter(func.extract('year', Holiday.date) == year)
    return q.order_by(Holiday.date.asc()).all()


# ── PAYROLL ───────────────────────────────────────────
@router.post("/payroll/generate", response_model=PayrollResponse, status_code=201)
async def generate_payroll(data: PayrollCreate, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    existing = db.query(Payroll).filter(
        Payroll.staff_id == data.staff_id,
        Payroll.month == data.month,
        Payroll.year == data.year
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Payroll already generated for this month")

    staff = db.query(StaffProfile).filter(StaffProfile.id == data.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Calculate working days & attendance
    _, total_days = calendar.monthrange(data.year, data.month)
    att_records = db.query(Attendance).filter(
        Attendance.staff_id == data.staff_id,
        func.extract('month', Attendance.date) == data.month,
        func.extract('year', Attendance.date) == data.year
    ).all()
    days_present = sum(1 for a in att_records if a.status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE])
    days_leave = sum(1 for a in att_records if a.status == AttendanceStatus.ON_LEAVE)
    days_absent = total_days - days_present - days_leave
    holidays = db.query(Holiday).filter(
        func.extract('month', Holiday.date) == data.month,
        func.extract('year', Holiday.date) == data.year
    ).count()
    working_days = total_days - holidays

    overtime_hours = sum(a.overtime_hours or 0 for a in att_records)
    overtime_pay = (staff.basic_salary / (working_days * 8)) * overtime_hours if working_days > 0 else 0

    # Per-day salary ratio
    ratio = days_present / working_days if working_days > 0 else 0

    # Earnings
    basic = round(staff.basic_salary * ratio, 2)
    hra = round(staff.hra * ratio, 2)
    da = round(staff.da * ratio, 2)
    ta = round(staff.ta * ratio, 2)
    medical = round(staff.medical_allowance * ratio, 2)
    other_allow = round(staff.other_allowance * ratio, 2)
    gross = round(basic + hra + da + ta + medical + other_allow + overtime_pay + data.bonus + data.arrears, 2)

    # Deductions
    pf_emp = round(basic * 0.12, 2) if staff.pf_applicable else 0
    pf_er = round(basic * 0.12, 2) if staff.pf_applicable else 0
    esi_emp = round(gross * 0.0075, 2) if staff.esi_applicable and gross <= 21000 else 0
    esi_er = round(gross * 0.0325, 2) if staff.esi_applicable and gross <= 21000 else 0
    prof_tax = staff.professional_tax if gross > 15000 else 0
    total_ded = round(pf_emp + esi_emp + prof_tax + data.tds + data.loan_deduction + data.advance_deduction + data.other_deduction, 2)
    net = round(gross - total_ded, 2)

    payroll_kwargs = dict(
        staff_id=data.staff_id, month=data.month, year=data.year,
        total_working_days=working_days, days_present=days_present,
        days_absent=days_absent, days_leave=days_leave,
        overtime_hours=overtime_hours,
        basic=basic, hra=hra, da=da, ta=ta,
        medical_allowance=medical, other_allowance=other_allow,
        overtime_pay=round(overtime_pay, 2), bonus=data.bonus, arrears=data.arrears,
        gross_salary=gross,
        pf_employee=pf_emp, pf_employer=pf_er,
        esi_employee=esi_emp, esi_employer=esi_er,
        professional_tax=prof_tax, tds=data.tds,
        loan_deduction=data.loan_deduction, advance_deduction=data.advance_deduction,
        other_deduction=data.other_deduction, total_deductions=total_ded,
        net_salary=net, remarks=data.remarks, processed_by=current_user.id
    )

    attempt_base = next_sequence_number(db, Payroll)
    payroll = None
    last_error = None
    for i in range(MAX_RETRIES):
        payroll = Payroll(
            payroll_number=f"PAY{data.year}{data.month:02d}{attempt_base + i:04d}",
            **payroll_kwargs
        )
        db.add(payroll)
        try:
            db.flush()
            last_error = None
            break
        except IntegrityError as e:
            db.rollback()
            last_error = e
            payroll = None
    if last_error:
        raise last_error
    db.commit()
    db.refresh(payroll)
    return payroll


@router.get("/payroll", response_model=list[PayrollResponse])
async def list_payrolls(staff_id: Optional[int] = None,
                         month: Optional[int] = None,
                         year: Optional[int] = None,
                         status: Optional[PayrollStatus] = None,
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    q = db.query(Payroll)
    if staff_id:
        q = q.filter(Payroll.staff_id == staff_id)
    if month:
        q = q.filter(Payroll.month == month)
    if year:
        q = q.filter(Payroll.year == year)
    if status:
        q = q.filter(Payroll.status == status)
    return q.order_by(Payroll.year.desc(), Payroll.month.desc()).limit(200).all()


@router.put("/payroll/{payroll_id}", response_model=PayrollResponse)
async def update_payroll(payroll_id: int, data: PayrollUpdate,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(payroll, field, value)
    db.commit()
    db.refresh(payroll)
    return payroll


@router.get("/payroll/{payroll_id}/payslip")
async def get_payslip(payroll_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    staff = db.query(StaffProfile).filter(StaffProfile.id == payroll.staff_id).first()
    from app.models.user import User as UserModel
    user = db.query(UserModel).filter(UserModel.id == staff.user_id).first() if staff else None
    dept = db.query(Department).filter(Department.id == staff.department_id).first() if staff and staff.department_id else None
    desig = db.query(Designation).filter(Designation.id == staff.designation_id).first() if staff and staff.designation_id else None
    return {
        "payroll_number": payroll.payroll_number,
        "employee": {"name": user.full_name if user else "N/A",
                     "code": staff.employee_code if staff else "N/A",
                     "department": dept.name if dept else "N/A",
                     "designation": desig.title if desig else "N/A",
                     "bank": staff.bank_name if staff else "N/A",
                     "account": staff.account_number if staff else "N/A",
                     "pan": staff.pan_number if staff else "N/A"},
        "period": {"month": payroll.month, "year": payroll.year},
        "attendance": {"total_working_days": payroll.total_working_days,
                       "days_present": payroll.days_present,
                       "days_absent": payroll.days_absent,
                       "days_leave": payroll.days_leave},
        "earnings": {"basic": payroll.basic, "hra": payroll.hra, "da": payroll.da,
                     "ta": payroll.ta, "medical": payroll.medical_allowance,
                     "other": payroll.other_allowance, "overtime": payroll.overtime_pay,
                     "bonus": payroll.bonus, "arrears": payroll.arrears,
                     "gross": payroll.gross_salary},
        "deductions": {"pf_employee": payroll.pf_employee, "esi_employee": payroll.esi_employee,
                       "professional_tax": payroll.professional_tax, "tds": payroll.tds,
                       "loan": payroll.loan_deduction, "advance": payroll.advance_deduction,
                       "other": payroll.other_deduction, "total": payroll.total_deductions},
        "net_salary": payroll.net_salary,
        "status": payroll.status
    }


@router.get("/dashboard/stats")
async def hr_stats(db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    today = date.today()
    total_staff = db.query(StaffProfile).filter(StaffProfile.is_active == True).count()
    present_today = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status == AttendanceStatus.PRESENT
    ).count()
    on_leave = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status == AttendanceStatus.ON_LEAVE
    ).count()
    pending_leaves = db.query(LeaveApplication).filter(
        LeaveApplication.status == LeaveStatus.PENDING
    ).count()
    return {"total_staff": total_staff, "present_today": present_today,
            "on_leave_today": on_leave, "pending_leave_approvals": pending_leaves,
            "absent_today": total_staff - present_today - on_leave}


# ── SALARY STRUCTURE (item 176) ─────────────────────────
@router.post("/salary-structures", response_model=SalaryStructureResponse, status_code=201)
async def create_salary_structure(data: SalaryStructureCreate, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    existing = db.query(SalaryStructure).filter(
        SalaryStructure.staff_id == data.staff_id, SalaryStructure.is_active == True).first()
    if existing:
        existing.is_active = False   # supersede rather than error - salary structures change over time

    structure = SalaryStructure(staff_id=data.staff_id, basic=data.basic)
    db.add(structure)
    db.flush()
    for comp in data.components:
        db.add(SalaryComponent(structure_id=structure.id, **comp.model_dump()))
    db.commit()
    db.refresh(structure)
    return structure


@router.get("/salary-structures/staff/{staff_id}", response_model=SalaryStructureResponse)
async def get_salary_structure(staff_id: int, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    structure = db.query(SalaryStructure).filter(
        SalaryStructure.staff_id == staff_id, SalaryStructure.is_active == True).first()
    if not structure:
        raise HTTPException(status_code=404, detail="No active salary structure for this staff member")
    return structure


@router.get("/salary-structures/staff/{staff_id}/compute")
async def compute_salary_from_structure(staff_id: int, db: Session = Depends(get_db),
                                         current_user: User = Depends(get_current_user)):
    """
    Applies each component's calc rule against the structure's basic to
    produce actual amounts - the piece that makes the structure usable
    for a monthly Payroll run instead of just being a reference document.
    """
    structure = db.query(SalaryStructure).filter(
        SalaryStructure.staff_id == staff_id, SalaryStructure.is_active == True).first()
    if not structure:
        raise HTTPException(status_code=404, detail="No active salary structure for this staff member")

    earnings, deductions = [], []
    gross = structure.basic
    for c in structure.components:
        if c.calc_type == "percent_of_basic":
            amount = round(structure.basic * c.value / 100, 2)
        elif c.calc_type == "fixed":
            amount = c.value
        else:
            amount = 0   # percent_of_gross resolved in a second pass below, once gross is known
        if c.is_earning:
            earnings.append({"component": c.component_name, "amount": amount})
            gross += amount

    for c in structure.components:
        if c.calc_type == "percent_of_gross":
            amount = round(gross * c.value / 100, 2)
            target = earnings if c.is_earning else deductions
            target.append({"component": c.component_name, "amount": amount})
            if c.is_earning:
                gross += amount
        elif not c.is_earning:
            amount = c.value if c.calc_type == "fixed" else round(structure.basic * c.value / 100, 2)
            deductions.append({"component": c.component_name, "amount": amount})

    total_deductions = sum(d["amount"] for d in deductions)
    return {
        "staff_id": staff_id, "basic": structure.basic,
        "earnings": earnings, "deductions": deductions,
        "gross_salary": round(gross, 2),
        "net_salary": round(gross - total_deductions, 2),
    }


# ── SHIFT ASSIGNMENT (item 173) ─────────────────────────
def _times_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    return start1 < end2 and start2 < end1


@router.post("/shift-assignments", response_model=ShiftAssignmentResponse, status_code=201)
async def create_shift_assignment(data: ShiftAssignmentCreate, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    """Rejects the assignment if it overlaps an existing active shift for
    the same staff member on the same date - the conflict check the
    checklist flagged as missing."""
    existing_shifts = db.query(ShiftAssignment).filter(
        ShiftAssignment.staff_id == data.staff_id,
        ShiftAssignment.shift_date == data.shift_date,
        ShiftAssignment.is_active == True,
    ).all()
    for s in existing_shifts:
        if _times_overlap(data.start_time, data.end_time, s.start_time, s.end_time):
            raise HTTPException(
                status_code=409,
                detail=f"Conflicts with existing shift '{s.shift_name}' ({s.start_time}-{s.end_time}) on {data.shift_date}"
            )

    assignment = ShiftAssignment(**data.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/shift-assignments", response_model=List[ShiftAssignmentResponse])
async def list_shift_assignments(staff_id: Optional[int] = None, shift_date: Optional[date] = None,
                                  department_id: Optional[int] = None, db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    q = db.query(ShiftAssignment).filter(ShiftAssignment.is_active == True)
    if staff_id:
        q = q.filter(ShiftAssignment.staff_id == staff_id)
    if shift_date:
        q = q.filter(ShiftAssignment.shift_date == shift_date)
    if department_id:
        q = q.filter(ShiftAssignment.department_id == department_id)
    return q.order_by(ShiftAssignment.shift_date, ShiftAssignment.start_time).all()


@router.delete("/shift-assignments/{assignment_id}", status_code=204)
async def cancel_shift_assignment(assignment_id: int, db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    assignment = db.query(ShiftAssignment).filter(ShiftAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Shift assignment not found")
    assignment.is_active = False
    db.commit()


