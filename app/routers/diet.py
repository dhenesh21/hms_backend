from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.diet import DietChart, MealEntry, DietType

router = APIRouter(prefix="/diet-charts", tags=["Diet & Nutrition"])


def _chart_to_dict(chart: DietChart):
    return {
        "id": chart.id,
        "admission_id": chart.admission_id,
        "patient_id": chart.patient_id,
        "diet_type": chart.diet_type,
        "special_instructions": chart.special_instructions,
        "allergies": chart.allergies,
        "is_active": chart.is_active,
        "prescribed_by": chart.prescribed_by,
        "created_at": chart.created_at,
        "meals": [
            {
                "id": m.id,
                "meal_type": m.meal_type,
                "meal_date": m.meal_date,
                "items": m.items,
                "calories": m.calories,
                "served": m.served,
                "consumed": m.consumed,
            }
            for m in chart.meals
        ],
    }


@router.post("", status_code=201)
async def create_diet_chart(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chart = DietChart(
        admission_id=data["admission_id"],
        patient_id=data["patient_id"],
        diet_type=data.get("diet_type", DietType.NORMAL),
        special_instructions=data.get("special_instructions"),
        allergies=data.get("allergies"),
        prescribed_by=data.get("prescribed_by", current_user.full_name),
    )
    db.add(chart)
    db.commit()
    db.refresh(chart)
    return _chart_to_dict(chart)


@router.get("/{admission_id}")
async def get_chart_by_admission(
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Matches the frontend's dietService.getChart(admissionId) contract -
    fetches the (most recent active) diet chart for an IPD admission."""
    chart = (
        db.query(DietChart)
        .filter(DietChart.admission_id == admission_id)
        .order_by(DietChart.created_at.desc())
        .first()
    )
    if not chart:
        raise HTTPException(status_code=404, detail="No diet chart found for this admission")
    return _chart_to_dict(chart)


@router.post("/{chart_id}/meals", status_code=201)
async def add_meal_entry(
    chart_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chart = db.query(DietChart).filter(DietChart.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Diet chart not found")
    meal = MealEntry(
        diet_chart_id=chart_id,
        meal_type=data["meal_type"],
        meal_date=data.get("meal_date", date.today()),
        items=data.get("items"),
        calories=data.get("calories"),
        notes=data.get("notes"),
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return {"id": meal.id, "meal_type": meal.meal_type, "meal_date": meal.meal_date}


@router.put("/meals/{meal_id}/serve")
async def mark_meal_served(
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from datetime import datetime
    meal = db.query(MealEntry).filter(MealEntry.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal entry not found")
    meal.served = True
    meal.served_at = datetime.utcnow()
    db.commit()
    return {"message": "Meal marked as served", "id": meal.id}


@router.put("/meals/{meal_id}/consume")
async def mark_meal_consumed(
    meal_id: int,
    data: dict = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meal = db.query(MealEntry).filter(MealEntry.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal entry not found")
    meal.consumed = data.get("consumed", True)
    db.commit()
    return {"message": "Meal consumption updated", "id": meal.id}


@router.get("/templates/{diet_type}")
async def get_diet_template(
    diet_type: str,
    current_user: User = Depends(get_current_user)
):
    """Static reference templates for common diet types (roadmap: 'Special Diet')."""
    templates = {
        "normal": {"description": "Regular balanced diet", "sample_meals": ["Rice/roti + dal + vegetable + curd"]},
        "diabetic": {"description": "Low sugar, controlled carbohydrate diet", "sample_meals": ["Multigrain roti + vegetable + dal", "Avoid sweets and refined sugar"]},
        "liquid": {"description": "Clear/full liquid diet for post-op or GI-rest patients", "sample_meals": ["Soup", "Fruit juice", "Milk"]},
        "soft": {"description": "Easy-to-chew, easy-to-digest soft foods", "sample_meals": ["Khichdi", "Mashed vegetables", "Curd rice"]},
        "renal": {"description": "Low sodium, low potassium, controlled protein diet", "sample_meals": ["Rice + limited-protein curry", "Avoid banana, coconut water"]},
        "cardiac": {"description": "Low sodium, low fat, heart-healthy diet", "sample_meals": ["Steamed vegetables", "Grilled fish/paneer", "Avoid fried food"]},
    }
    return templates.get(diet_type, {"description": "No template available", "sample_meals": []})

