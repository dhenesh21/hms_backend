from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Text, Float, Boolean, Enum, Date, JSON, Time)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class EmploymentType(str, enum.Enum):
    PERMANENT = "permanent"
    CONTRACT = "contract"
    PROBATION = "probation"
    INTERN = "intern"
    CONSULTANT = "consultant"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    HALF_DAY = "half_day"
    LATE = "late"
    ON_LEAVE = "on_leave"
    HOLIDAY = "holiday"
    WEEKLY_OFF = "weekly_off"


class LeaveType(str, enum.Enum):
    CASUAL = "casual"
    SICK = "sick"
    EARNED = "earned"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    COMPENSATORY = "compensatory"
    UNPAID = "unpaid"
    EMERGENCY = "emergency"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PayrollStatus(str, enum.Enum):
    DRAFT = "draft"
    PROCESSED = "processed"
    PAID = "paid"
    HOLD = "hold"


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    dept_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    head_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff = relationship("StaffProfile", back_populates="department",
                         foreign_keys="StaffProfile.department_id")


class Designation(Base):
    __tablename__ = "designations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    grade = Column(String(20))
    basic_salary_min = Column(Float, default=0)
    basic_salary_max = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_code = Column(String(20), unique=True, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    designation_id = Column(Integer, ForeignKey("designations.id"))
    employment_type = Column(Enum(EmploymentType), default=EmploymentType.PERMANENT)

    # Personal
    date_of_birth = Column(Date)
    gender = Column(String(10))
    blood_group = Column(String(5))
    marital_status = Column(String(20))
    nationality = Column(String(50), default="Indian")
    aadhar_number = Column(String(12))
    pan_number = Column(String(10))

    # Contact
    personal_email = Column(String(200))
    personal_phone = Column(String(20))
    emergency_contact = Column(String(200))
    emergency_phone = Column(String(20))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    pincode = Column(String(10))

    # Employment
    date_of_joining = Column(Date, nullable=False)
    date_of_leaving = Column(Date)
    reporting_manager_id = Column(Integer, ForeignKey("staff_profiles.id"))
    shift = Column(String(50), default="General")  # General, Morning, Evening, Night
    weekly_off = Column(JSON, default=["Sunday"])

    # Bank details
    bank_name = Column(String(200))
    account_number = Column(String(50))
    ifsc_code = Column(String(20))
    account_holder_name = Column(String(200))

    # Salary
    basic_salary = Column(Float, default=0)
    hra = Column(Float, default=0)
    da = Column(Float, default=0)
    ta = Column(Float, default=0)
    medical_allowance = Column(Float, default=0)
    other_allowance = Column(Float, default=0)
    pf_applicable = Column(Boolean, default=True)
    esi_applicable = Column(Boolean, default=False)
    professional_tax = Column(Float, default=200)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    department = relationship("Department", back_populates="staff",
                              foreign_keys=[department_id])
    designation = relationship("Designation")
    attendance = relationship("Attendance", back_populates="staff")
    leaves = relationship("LeaveApplication", back_populates="staff")
    payrolls = relationship("Payroll", back_populates="staff")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    check_in = Column(String(10))   # "09:00"
    check_out = Column(String(10))  # "17:00"
    working_hours = Column(Float, default=0)
    overtime_hours = Column(Float, default=0)
    late_minutes = Column(Integer, default=0)
    remarks = Column(Text)
    marked_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    staff = relationship("StaffProfile", back_populates="attendance")


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    year = Column(Integer, nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    total_days = Column(Float, default=0)
    used_days = Column(Float, default=0)
    pending_days = Column(Float, default=0)
    balance_days = Column(Float, default=0)
    carried_forward = Column(Float, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LeaveApplication(Base):
    __tablename__ = "leave_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_number = Column(String(20), unique=True, nullable=False)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    total_days = Column(Float, nullable=False)
    half_day = Column(Boolean, default=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    contact_during_leave = Column(String(20))
    handover_notes = Column(Text)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    staff = relationship("StaffProfile", back_populates="leaves")


class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    date = Column(Date, nullable=False, unique=True)
    holiday_type = Column(String(50), default="national")  # national, optional, restricted
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ComponentCalcType(str, enum.Enum):
    FIXED = "fixed"
    PERCENT_OF_BASIC = "percent_of_basic"
    PERCENT_OF_GROSS = "percent_of_gross"


class SalaryStructure(Base):
    """
    Item 176 — the checklist gap wasn't that Payroll lacks line items (it
    already has basic/hra/da/ta/medical/other/overtime/bonus/arrears +
    deductions per month), it's that nothing DEFINED what those numbers
    should be — each month's Payroll was apparently populated ad hoc. This
    is the per-staff template: which components apply and how each is
    calculated (fixed amount, or a percentage of basic/gross), so a
    monthly Payroll run can derive its line items from a rule instead of
    manual re-entry every month. One active structure per staff member.
    """
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False, unique=True)
    basic = Column(Float, nullable=False)
    effective_from = Column(Date, server_default=func.current_date())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    components = relationship("SalaryComponent", back_populates="structure")


class SalaryComponent(Base):
    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True)
    structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=False)
    component_name = Column(String(100), nullable=False)   # "HRA", "DA", "PF Employee", "ESI"
    is_earning = Column(Boolean, default=True)              # False = deduction
    calc_type = Column(Enum(ComponentCalcType), default=ComponentCalcType.FIXED)
    value = Column(Float, nullable=False)   # fixed amount, or the percentage (e.g. 40 for 40%)

    structure = relationship("SalaryStructure", back_populates="components")


class ShiftAssignment(Base):
    """
    Item 173 — general staff shift scheduling (any staff type), distinct
    from Group 4's `NurseWardAssignment` (which is nurse-specific and about
    WHICH WARD a nurse covers, not shift-time conflict prevention). This is
    what the checklist actually asked for: preventing the same staff member
    from being scheduled into two overlapping shifts on the same day. The
    conflict check itself lives in the router (query for an overlapping
    active assignment before inserting), not as a DB constraint, since
    "overlapping" needs a time-range comparison a simple UNIQUE constraint
    can't express.
    """
    __tablename__ = "shift_assignments"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    shift_date = Column(Date, nullable=False)
    shift_name = Column(String(50), nullable=False)   # "Morning", "Evening", "Night"
    start_time = Column(String(5), nullable=False)     # "08:00"
    end_time = Column(String(5), nullable=False)        # "16:00"
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payroll(Base):
    __tablename__ = "payrolls"

    id = Column(Integer, primary_key=True, index=True)
    payroll_number = Column(String(20), unique=True, nullable=False)
    staff_id = Column(Integer, ForeignKey("staff_profiles.id"), nullable=False)
    month = Column(Integer, nullable=False)   # 1-12
    year = Column(Integer, nullable=False)
    status = Column(Enum(PayrollStatus), default=PayrollStatus.DRAFT)

    # Working days
    total_working_days = Column(Integer, default=0)
    days_present = Column(Integer, default=0)
    days_absent = Column(Integer, default=0)
    days_leave = Column(Integer, default=0)
    overtime_hours = Column(Float, default=0)

    # Earnings
    basic = Column(Float, default=0)
    hra = Column(Float, default=0)
    da = Column(Float, default=0)
    ta = Column(Float, default=0)
    medical_allowance = Column(Float, default=0)
    other_allowance = Column(Float, default=0)
    overtime_pay = Column(Float, default=0)
    bonus = Column(Float, default=0)
    arrears = Column(Float, default=0)
    gross_salary = Column(Float, default=0)

    # Deductions
    pf_employee = Column(Float, default=0)   # 12% of basic
    pf_employer = Column(Float, default=0)   # 12% of basic
    esi_employee = Column(Float, default=0)  # 0.75% of gross
    esi_employer = Column(Float, default=0)  # 3.25% of gross
    professional_tax = Column(Float, default=0)
    tds = Column(Float, default=0)
    loan_deduction = Column(Float, default=0)
    advance_deduction = Column(Float, default=0)
    other_deduction = Column(Float, default=0)
    total_deductions = Column(Float, default=0)

    # Net
    net_salary = Column(Float, default=0)

    payment_date = Column(Date)
    payment_mode = Column(String(50))
    transaction_reference = Column(String(200))
    remarks = Column(Text)
    processed_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    staff = relationship("StaffProfile", back_populates="payrolls")
