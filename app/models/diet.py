import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class DietType(str, enum.Enum):
    NORMAL = "normal"; SOFT = "soft"; LIQUID = "liquid"
    NPO = "npo"; DIABETIC = "diabetic"; LOW_SODIUM = "low_sodium"
    HIGH_PROTEIN = "high_protein"; LOW_FAT = "low_fat"; RENAL = "renal"


class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"; MID_MORNING = "mid_morning"
    LUNCH = "lunch"; EVENING = "evening"; DINNER = "dinner"


class DietChart(Base):
    __tablename__ = "diet_charts"
    id = Column(Integer, primary_key=True, index=True)
    admission_id = Column(Integer, ForeignKey("ipd_admissions.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    diet_type = Column(Enum(DietType), default=DietType.NORMAL)
    special_instructions = Column(Text)
    allergies = Column(String(300))
    is_active = Column(Boolean, default=True)
    prescribed_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meals = relationship("MealEntry", back_populates="diet_chart")


class MealEntry(Base):
    __tablename__ = "meal_entries"
    id = Column(Integer, primary_key=True, index=True)
    diet_chart_id = Column(Integer, ForeignKey("diet_charts.id"), nullable=False)
    meal_type = Column(Enum(MealType), nullable=False)
    meal_date = Column(Date, nullable=False)
    items = Column(Text)
    calories = Column(Integer)
    served = Column(Boolean, default=False)
    consumed = Column(Boolean, default=False)
    notes = Column(String(300))
    served_at = Column(DateTime, nullable=True)
    diet_chart = relationship("DietChart", back_populates="meals")
