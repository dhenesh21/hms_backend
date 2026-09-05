from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.appointment import Appointment
from app.models.lab import LabOrder
from app.models.pharmacy import DrugMaster, DrugStock
from app.models.billing import Bill, BillStatus
from app.models.ipd import IPDAdmission, IPDStatus

router = APIRouter(tags=["Notifications"])


@router.get("/notifications")
async def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    notifications = []

    # Today's appointments
    try:
        appts = db.query(Appointment).filter(
            Appointment.appointment_date == today,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count()
        if appts > 0:
            notifications.append({
                "id": "appt-today",
                "type": "appointment",
                "title": f"{appts} appointment(s) today",
                "message": "Patients scheduled for today",
                "priority": "info",
                "icon": "calendar",
                "link": "/appointments"
            })
    except Exception:
        pass

    # Low stock drugs
    try:
        low_stock = db.query(DrugMaster).filter(DrugMaster.is_active == True).all()
        low_count = 0
        for drug in low_stock:
            total = sum(s.quantity_remaining for s in drug.stock_batches if s.is_active)
            if total <= drug.reorder_level:
                low_count += 1
        if low_count > 0:
            notifications.append({
                "id": "low-stock",
                "type": "pharmacy",
                "title": f"{low_count} drug(s) low on stock",
                "message": "Reorder required for these medicines",
                "priority": "warning",
                "icon": "pill",
                "link": "/pharmacy"
            })
    except Exception:
        pass

    # Expiring drugs (within 30 days)
    try:
        expiry_date = today + timedelta(days=30)
        expiring = db.query(DrugStock).filter(
            DrugStock.expiry_date <= expiry_date,
            DrugStock.expiry_date >= today,
            DrugStock.is_active == True,
            DrugStock.quantity_remaining > 0
        ).count()
        if expiring > 0:
            notifications.append({
                "id": "expiring-drugs",
                "type": "pharmacy",
                "title": f"{expiring} drug batch(es) expiring soon",
                "message": "Within 30 days — review inventory",
                "priority": "warning",
                "icon": "alert",
                "link": "/pharmacy"
            })
    except Exception:
        pass

    # Overdue bills
    try:
        overdue = db.query(Bill).filter(
            Bill.payment_status == BillStatus.PENDING,
            Bill.due_date < today
        ).count() if hasattr(Bill, 'due_date') else 0
        if overdue > 0:
            notifications.append({
                "id": "overdue-bills",
                "type": "billing",
                "title": f"{overdue} overdue bill(s)",
                "message": "Payment pending past due date",
                "priority": "error",
                "icon": "receipt",
                "link": "/billing"
            })
    except Exception:
        pass

    # Pending lab results
    try:
        pending_lab = db.query(LabOrder).filter(
            LabOrder.status == 'collected'
        ).count()
        if pending_lab > 0:
            notifications.append({
                "id": "lab-pending",
                "type": "lab",
                "title": f"{pending_lab} lab result(s) pending",
                "message": "Samples collected, awaiting results",
                "priority": "info",
                "icon": "flask",
                "link": "/lab"
            })
    except Exception:
        pass

    # Long IPD stays (> 14 days)
    try:
        threshold = today - timedelta(days=14)
        long_stay = db.query(IPDAdmission).filter(
            IPDAdmission.status == IPDStatus.ADMITTED,
            IPDAdmission.admission_date <= threshold
        ).count()
        if long_stay > 0:
            notifications.append({
                "id": "long-stay",
                "type": "ipd",
                "title": f"{long_stay} patient(s) with long stay (>14 days)",
                "message": "Review discharge plan",
                "priority": "warning",
                "icon": "bed",
                "link": "/ipd"
            })
    except Exception:
        pass

    return {
        "count": len(notifications),
        "notifications": notifications
    }
