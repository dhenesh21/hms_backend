from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nurse_roster import NurseWardAssignment
from app.models.user import User
from app.schemas.nurse_roster import NurseAssignmentCreate, NurseAssignmentResponse

router = APIRouter(prefix="/nurse-roster", tags=["Nurse Ward Roster"])


@router.post("/assignments", response_model=NurseAssignmentResponse, status_code=201)
async def assign_nurse_to_ward(data: NurseAssignmentCreate, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    assignment = NurseWardAssignment(**data.model_dump(), assigned_by=current_user.id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/assignments", response_model=List[NurseAssignmentResponse])
async def list_assignments(ward_id: Optional[int] = None, nurse_id: Optional[int] = None,
                            assignment_date: Optional[date] = None, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    q = db.query(NurseWardAssignment)
    if ward_id:
        q = q.filter(NurseWardAssignment.ward_id == ward_id)
    if nurse_id:
        q = q.filter(NurseWardAssignment.nurse_id == nurse_id)
    if assignment_date:
        q = q.filter(NurseWardAssignment.assignment_date == assignment_date)
    return q.all()


@router.get("/my-wards-today", response_model=List[NurseAssignmentResponse])
async def my_wards_today(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """What Nurse Portal should call to scope 'my ward' instead of taking ward_id blind."""
    return db.query(NurseWardAssignment).filter(
        NurseWardAssignment.nurse_id == current_user.id,
        NurseWardAssignment.assignment_date == date.today(),
    ).all()
