from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import date, datetime
from app.models.reports import ReportType, ReportFormat


class DateRangeFilter(BaseModel):
    from_date: date
    to_date: date


class ReportRequest(BaseModel):
    report_type: ReportType
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    filters: Optional[Dict[str, Any]] = {}
    format: ReportFormat = ReportFormat.JSON
    save: bool = False
    name: Optional[str] = None


class SavedReportResponse(BaseModel):
    id: int
    name: str
    report_type: ReportType
    parameters: Dict
    format: ReportFormat
    generated_at: datetime
    file_size_kb: Optional[int]
    class Config:
        from_attributes = True


class ReportScheduleCreate(BaseModel):
    name: str
    report_type: ReportType
    frequency: str
    send_to_emails: List[str] = []
    parameters: Dict[str, Any] = {}


class ReportScheduleResponse(BaseModel):
    id: int
    name: str
    report_type: ReportType
    frequency: str
    send_to_emails: List[str]
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    is_active: bool
    class Config:
        from_attributes = True


# Report data models
class OPDSummaryData(BaseModel):
    total_visits: int
    new_patients: int
    follow_ups: int
    by_doctor: List[Dict]
    by_department: List[Dict]
    by_day: List[Dict]


class IPDSummaryData(BaseModel):
    total_admissions: int
    total_discharges: int
    current_occupancy: int
    avg_length_of_stay: float
    by_ward: List[Dict]
    by_doctor: List[Dict]


class RevenueData(BaseModel):
    total_revenue: float
    opd_revenue: float
    ipd_revenue: float
    pharmacy_revenue: float
    lab_revenue: float
    radiology_revenue: float
    by_day: List[Dict]
    by_payment_mode: Dict[str, float]


class MISData(BaseModel):
    period: str
    opd: Dict
    ipd: Dict
    revenue: Dict
    pharmacy: Dict
    lab: Dict
    insurance: Dict
