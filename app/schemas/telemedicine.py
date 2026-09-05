from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.telemedicine import ConsultationStatus


class VirtualConsultCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int] = None
    scheduled_at: datetime
    is_second_opinion: bool = False
    referring_doctor_id: Optional[int] = None
    reason_for_consult: Optional[str] = None
    meeting_provider: Optional[str] = None
    meeting_link: Optional[str] = None


class VirtualConsultUpdate(BaseModel):
    meeting_provider: Optional[str] = None
    meeting_link: Optional[str] = None
    meeting_id_external: Optional[str] = None


class VirtualConsultComplete(BaseModel):
    consultation_notes: str
    prescription_issued: bool = False
    follow_up_advised: bool = False


class VirtualConsultCancel(BaseModel):
    cancellation_reason: str


class VirtualConsultResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    status: ConsultationStatus
    meeting_provider: Optional[str]
    meeting_link: Optional[str]
    is_second_opinion: bool
    referring_doctor_id: Optional[int]
    reason_for_consult: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_minutes: Optional[int]
    consultation_notes: Optional[str]

    class Config:
        from_attributes = True
