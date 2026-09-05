from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.hr import EmploymentType, AttendanceStatus, LeaveType, LeaveStatus, PayrollStatus


class DepartmentCreate(BaseModel):
    branch_id: Optional[int] = None
    dept_code: str
    name: str
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: int
    branch_id: Optional[int]
    dept_code: str
    name: str
    description: Optional[str]
    is_active: bool
    class Config:
        from_attributes = True


class DesignationCreate(BaseModel):
    title: str
    department_id: Optional[int] = None
    grade: Optional[str] = None
    basic_salary_min: float = 0
    basic_salary_max: float = 0


class DesignationResponse(BaseModel):
    id: int
    title: str
    department_id: Optional[int]
    grade: Optional[str]
    basic_salary_min: float
    basic_salary_max: float
    is_active: bool
    class Config:
        from_attributes = True


class StaffProfileCreate(BaseModel):
    user_id: int
    employee_code: str
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    employment_type: EmploymentType = EmploymentType.PERMANENT
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    marital_status: Optional[str] = None
    aadhar_number: Optional[str] = None
    pan_number: Optional[str] = None
    personal_email: Optional[str] = None
    personal_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    date_of_joining: date
    shift: str = "General"
    weekly_off: List[str] = ["Sunday"]
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_holder_name: Optional[str] = None
    basic_salary: float = 0
    hra: float = 0
    da: float = 0
    ta: float = 0
    medical_allowance: float = 0
    other_allowance: float = 0
    pf_applicable: bool = True
    esi_applicable: bool = False
    professional_tax: float = 200


class StaffProfileUpdate(BaseModel):
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    shift: Optional[str] = None
    basic_salary: Optional[float] = None
    hra: Optional[float] = None
    da: Optional[float] = None
    ta: Optional[float] = None
    medical_allowance: Optional[float] = None
    other_allowance: Optional[float] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    is_active: Optional[bool] = None


class StaffProfileResponse(BaseModel):
    id: int
    user_id: int
    employee_code: str
    department_id: Optional[int]
    designation_id: Optional[int]
    employment_type: EmploymentType
    date_of_birth: Optional[date]
    gender: Optional[str]
    personal_phone: Optional[str]
    date_of_joining: date
    shift: str
    basic_salary: float
    hra: float
    da: float
    ta: float
    medical_allowance: float
    other_allowance: float
    pf_applicable: bool
    esi_applicable: bool
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True


class StaffListResponse(BaseModel):
    id: int
    employee_code: str
    full_name: str
    department_name: Optional[str]
    designation_title: Optional[str]
    employment_type: EmploymentType
    shift: str
    date_of_joining: date
    is_active: bool


class AttendanceCreate(BaseModel):
    staff_id: int
    date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    remarks: Optional[str] = None


class AttendanceBulkCreate(BaseModel):
    date: date
    records: List[AttendanceCreate]


class AttendanceResponse(BaseModel):
    id: int
    staff_id: int
    date: date
    status: AttendanceStatus
    check_in: Optional[str]
    check_out: Optional[str]
    working_hours: float
    overtime_hours: float
    late_minutes: int
    remarks: Optional[str]
    class Config:
        from_attributes = True


class LeaveApplicationCreate(BaseModel):
    staff_id: int
    leave_type: LeaveType
    from_date: date
    to_date: date
    half_day: bool = False
    reason: str
    contact_during_leave: Optional[str] = None
    handover_notes: Optional[str] = None


class LeaveApprovalRequest(BaseModel):
    status: LeaveStatus
    rejection_reason: Optional[str] = None


class LeaveApplicationResponse(BaseModel):
    id: int
    application_number: str
    staff_id: int
    leave_type: LeaveType
    from_date: date
    to_date: date
    total_days: float
    half_day: bool
    reason: str
    status: LeaveStatus
    rejection_reason: Optional[str]
    applied_at: datetime
    class Config:
        from_attributes = True


class LeaveBalanceResponse(BaseModel):
    id: int
    staff_id: int
    year: int
    leave_type: LeaveType
    total_days: float
    used_days: float
    pending_days: float
    balance_days: float
    class Config:
        from_attributes = True


class HolidayCreate(BaseModel):
    name: str
    date: date
    holiday_type: str = "national"
    description: Optional[str] = None


class HolidayResponse(BaseModel):
    id: int
    name: str
    date: date
    holiday_type: str
    description: Optional[str]
    class Config:
        from_attributes = True


class PayrollCreate(BaseModel):
    staff_id: int
    month: int
    year: int
    bonus: float = 0
    arrears: float = 0
    loan_deduction: float = 0
    advance_deduction: float = 0
    other_deduction: float = 0
    tds: float = 0
    remarks: Optional[str] = None


class PayrollUpdate(BaseModel):
    status: Optional[PayrollStatus] = None
    payment_date: Optional[date] = None
    payment_mode: Optional[str] = None
    transaction_reference: Optional[str] = None
    bonus: Optional[float] = None
    other_deduction: Optional[float] = None
    remarks: Optional[str] = None


class PayrollResponse(BaseModel):
    id: int
    payroll_number: str
    staff_id: int
    month: int
    year: int
    status: PayrollStatus
    total_working_days: int
    days_present: int
    days_absent: int
    days_leave: int
    basic: float
    hra: float
    da: float
    ta: float
    medical_allowance: float
    other_allowance: float
    overtime_pay: float
    bonus: float
    gross_salary: float
    pf_employee: float
    esi_employee: float
    professional_tax: float
    tds: float
    loan_deduction: float
    advance_deduction: float
    other_deduction: float
    total_deductions: float
    net_salary: float
    payment_date: Optional[date]
    payment_mode: Optional[str]
    class Config:
        from_attributes = True


# ── SALARY STRUCTURE (item 176) ─────────────────────────
class SalaryComponentCreate(BaseModel):
    component_name: str
    is_earning: bool = True
    calc_type: str = "fixed"   # fixed, percent_of_basic, percent_of_gross
    value: float


class SalaryComponentResponse(BaseModel):
    id: int
    component_name: str
    is_earning: bool
    calc_type: str
    value: float
    class Config:
        from_attributes = True


class SalaryStructureCreate(BaseModel):
    staff_id: int
    basic: float
    components: List[SalaryComponentCreate] = []


class SalaryStructureResponse(BaseModel):
    id: int
    staff_id: int
    basic: float
    effective_from: date
    is_active: bool
    components: List[SalaryComponentResponse] = []
    class Config:
        from_attributes = True


# ── SHIFT ASSIGNMENT (item 173) ─────────────────────────
class ShiftAssignmentCreate(BaseModel):
    staff_id: int
    shift_date: date
    shift_name: str
    start_time: str
    end_time: str
    department_id: Optional[int] = None


class ShiftAssignmentResponse(BaseModel):
    id: int
    staff_id: int
    shift_date: date
    shift_name: str
    start_time: str
    end_time: str
    department_id: Optional[int]
    class Config:
        from_attributes = True
