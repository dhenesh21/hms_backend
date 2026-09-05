import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.doctor import DoctorProfile
from app.models.patient import Patient

router = APIRouter(tags=["Upload"])

UPLOAD_DIR = "uploads/photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


def save_photo(file: UploadFile) -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, WEBP allowed")
    content = file.file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    return f"/uploads/photos/{filename}"


@router.post("/upload/user-photo/{user_id}")
async def upload_user_photo(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Delete old photo if exists
    if user.photo_url:
        old_path = user.photo_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)
    url = save_photo(file)
    user.photo_url = url
    db.commit()
    return {"photo_url": url}


@router.post("/upload/doctor-photo/{doctor_id}")
async def upload_doctor_photo(
    doctor_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if doctor.photo_url:
        old_path = doctor.photo_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)
    url = save_photo(file)
    doctor.photo_url = url
    db.commit()
    return {"photo_url": url}


@router.post("/upload/patient-photo/{patient_id}")
async def upload_patient_photo(
    patient_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if patient.photo_url:
        old_path = patient.photo_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)
    url = save_photo(file)
    patient.photo_url = url
    db.commit()
    return {"photo_url": url}


@router.delete("/upload/user-photo/{user_id}")
async def delete_user_photo(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.photo_url:
        old_path = user.photo_url.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)
        user.photo_url = None
        db.commit()
    return {"message": "Photo removed"}
