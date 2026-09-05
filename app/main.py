from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.models import *
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.routers import auth, patients, doctors, opd, ipd, emr, lab, radiology, ot, billing, pharmacy, insurance, hr, nursing, reports, admin, upload, notifications, blood_bank, diet, notify, referral, emergency, critical_care, ambulance, birth_register, mortuary, housekeeping, infection_control, front_desk, cssd, facility, security_incident, cpoe, consent, clinical_forms, care_plan, clinical_timeline, anesthesia, recovery_room, physiotherapy, pain_management, palliative_care, patient_portal, doctor_portal, nurse_portal, telemedicine, preventive_health, family, patient_category, cds, nurse_roster, dialysis, mental_health, fertility, oncology, transplant, mpi, provider_registry, facility_registry, terminology, data_governance, fhir, hl7, data_exchange, identity_provider, dicom, payment_gateway, inventory, accounts, medical_coding, organization, medical_record_privacy, report_template, analytics
from app.models import cpoe as cpoe_models
from app.models import consent as consent_models
from app.models import clinical_forms as clinical_forms_models
from app.models import care_plan as care_plan_models
from app.models import blood_bank as bb_models
from app.models import diet as diet_models
from app.models import referral as referral_models
from app.models import emergency as emergency_models
from app.models import critical_care as critical_care_models
from app.models import ambulance as ambulance_models
from app.models import birth_register as birth_register_models
from app.models import mortuary as mortuary_models
from app.models import housekeeping as housekeeping_models
from app.models import infection_control as infection_control_models
from app.models import front_desk as front_desk_models
from app.models import cssd as cssd_models
from app.models import facility as facility_models
from app.models import security_incident as security_incident_models
from app.models import inventory as inventory_models
from app.models import accounts as accounts_models
from app.models import medical_coding as medical_coding_models
from app.models import organization as organization_models
from app.models import report_template as report_template_models
import os
import logging
import time
import uuid

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import limiter
import os

# Create all tables
Base.metadata.create_all(bind=engine)

# Ensure upload directory exists
os.makedirs("uploads/photos", exist_ok=True)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Hospital Management System - Phase 1 API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiting - roadmap's "Rate Limiting". Keyed by client IP; the
# global default guards against runaway/scripted traffic on any endpoint,
# and specific endpoints (like login, see auth.py) can apply a stricter
# limit for brute-force protection.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("hms")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@app.middleware("http")
async def request_logging_middleware(request, call_next):
    """
    Structured request logging with correlation IDs - roadmap's
    'Distributed Logging/Tracing'. Every request gets a unique ID that's
    both logged and returned in the X-Request-ID response header, so a
    single request can be traced through logs even across multiple
    service instances, and a person reporting an error can hand back the
    ID from their response headers to make finding it in logs trivial.
    """
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        '{"request_id": "%s", "method": "%s", "path": "%s", "status": %d, "duration_ms": %s}',
        request_id, request.method, request.url.path, response.status_code, duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(auth.router,      prefix="/api")
app.include_router(patients.router,  prefix="/api")
app.include_router(doctors.router,   prefix="/api")
app.include_router(opd.router,       prefix="/api")
app.include_router(ipd.router,       prefix="/api")
app.include_router(emr.router,       prefix="/api")
app.include_router(lab.router,       prefix="/api")
app.include_router(radiology.router, prefix="/api")
app.include_router(ot.router,        prefix="/api")
app.include_router(billing.router,   prefix="/api")
app.include_router(pharmacy.router,  prefix="/api")
app.include_router(insurance.router, prefix="/api")
app.include_router(hr.router,        prefix="/api")
app.include_router(nursing.router,   prefix="/api")
app.include_router(reports.router,   prefix="/api")
app.include_router(admin.router,     prefix="/api")
app.include_router(upload.router,          prefix="/api")
app.include_router(notifications.router,   prefix="/api")
app.include_router(blood_bank.router,      prefix="/api")
app.include_router(diet.router,            prefix="/api")
app.include_router(notify.router,          prefix="/api")
app.include_router(referral.router,        prefix="/api")
app.include_router(emergency.router,       prefix="/api")
app.include_router(critical_care.router,   prefix="/api")
app.include_router(ambulance.router,       prefix="/api")
app.include_router(birth_register.router,  prefix="/api")
app.include_router(mortuary.router,        prefix="/api")
app.include_router(housekeeping.router,    prefix="/api")
app.include_router(infection_control.router, prefix="/api")
app.include_router(front_desk.router,      prefix="/api")
app.include_router(cssd.router,            prefix="/api")
app.include_router(facility.router,        prefix="/api")
app.include_router(security_incident.router, prefix="/api")
app.include_router(cpoe.router,           prefix="/api")
app.include_router(consent.router,        prefix="/api")
app.include_router(clinical_forms.router, prefix="/api")
app.include_router(care_plan.router,      prefix="/api")
app.include_router(clinical_timeline.router, prefix="/api")
app.include_router(anesthesia.router,      prefix="/api")
app.include_router(recovery_room.router,   prefix="/api")
app.include_router(physiotherapy.router,   prefix="/api")
app.include_router(pain_management.router, prefix="/api")
app.include_router(palliative_care.router, prefix="/api")
app.include_router(patient_portal.router,  prefix="/api")
app.include_router(doctor_portal.router,   prefix="/api")
app.include_router(nurse_portal.router,    prefix="/api")
app.include_router(telemedicine.router,      prefix="/api")
app.include_router(preventive_health.router, prefix="/api")
app.include_router(family.router,            prefix="/api")
app.include_router(patient_category.router,  prefix="/api")
app.include_router(cds.router,               prefix="/api")
app.include_router(nurse_roster.router,      prefix="/api")
app.include_router(dialysis.router,          prefix="/api")
app.include_router(mental_health.router,     prefix="/api")
app.include_router(fertility.router,         prefix="/api")
app.include_router(oncology.router,          prefix="/api")
app.include_router(transplant.router,        prefix="/api")
app.include_router(mpi.router,               prefix="/api")
app.include_router(provider_registry.router, prefix="/api")
app.include_router(facility_registry.router, prefix="/api")
app.include_router(terminology.router,       prefix="/api")
app.include_router(data_governance.router,   prefix="/api")
app.include_router(fhir.router,              prefix="/api")
app.include_router(hl7.router,               prefix="/api")
app.include_router(data_exchange.router,     prefix="/api")
app.include_router(identity_provider.router, prefix="/api")
app.include_router(dicom.router,             prefix="/api")
app.include_router(payment_gateway.router,   prefix="/api")
app.include_router(inventory.router,       prefix="/api")
app.include_router(accounts.router,        prefix="/api")
app.include_router(medical_coding.router,  prefix="/api")
app.include_router(organization.router,    prefix="/api")
app.include_router(medical_record_privacy.router, prefix="/api")
app.include_router(report_template.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# Serve uploaded photos as static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} v{settings.VERSION}", "docs": "/docs"}


@app.get("/health")
async def health():
    """
    Liveness check: is the process itself up? Deliberately does NOT touch
    the database - a liveness probe should only fail if the app itself
    is deadlocked/crashed, not because a dependency is briefly down
    (orchestrators kill and restart containers that fail liveness,
    which would make a transient DB blip cause an unnecessary restart).
    """
    return {"status": "healthy"}


def check_database_connection() -> tuple[bool, str | None]:
    """Returns (is_connected, error_message). Kept separate from the
    endpoint so it can be unit-tested against a deliberately broken
    connection, proving this check can actually fail - not just always
    report healthy regardless of real DB state."""
    from sqlalchemy import text
    from app.core.database import SessionLocal

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return True, None
        finally:
            db.close()
    except Exception as e:
        return False, str(e)


@app.get("/health/ready")
async def health_ready():
    """
    Readiness check: can this instance actually serve requests right now?
    Unlike /health, this verifies the database connection - a previous
    version of this endpoint always returned "healthy" even when the DB
    was unreachable, which would have let a load balancer keep sending
    traffic to an instance that can't actually do anything.
    """
    db_ok, error_detail = check_database_connection()
    status_code = 200 if db_ok else 503
    body = {"status": "ready" if db_ok else "not_ready", "database": "connected" if db_ok else "unreachable"}
    if error_detail and not db_ok:
        body["error"] = error_detail
    return JSONResponse(status_code=status_code, content=body)
