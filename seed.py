"""
MASTER HMS SEED FILE
Run:
    docker-compose exec backend python seed_all.py
"""

import sys
sys.path.append(".")

from datetime import date, timedelta, time

from app.core.database import SessionLocal
from app.core.security import get_password_hash

# =========================
# MODELS
# =========================

# USERS
from app.models.user import User, UserRole

# DOCTOR
from app.models.doctor import DoctorProfile, DutyRoster

# PATIENT
from app.models.patient import Patient

# IPD
from app.models.ipd import Ward, Bed, WardType, BedStatus

# LAB
from app.models.lab import LabTest, LabCategory

# OT
from app.models.ot import OperationTheatre, OTStatus

# BILLING
from app.models.billing import (
    ServiceMaster,
    BillingPackage,
    ServiceCategory
)

# PHARMACY
from app.models.pharmacy import (
    DrugMaster,
    DrugStock,
    PharmacySupplier,
    DrugCategory,
    DrugFormulation
)

# INSURANCE
from app.models.insurance import InsuranceCompany

# HR
from app.models.hr import (
    Department,
    Designation,
    Holiday
)

# =========================================================
# PHASE 1
# =========================================================

def seed_users(db):

    print("\n🚀 Seeding Users...")

    if db.query(User).count() > 0:
        print("✅ Users already seeded")
        return

    users = [
        {
            "employee_id": "AD0001",
            "email": "admin@hospital.com",
            "password": "Admin@123",
            "full_name": "System Administrator",
            "role": UserRole.ADMIN,
            "department": "Administration",
            "is_superuser": True
        },
        {
            "employee_id": "DR0001",
            "email": "doctor@hospital.com",
            "password": "Doctor@123",
            "full_name": "Dr. Rajesh Kumar",
            "role": UserRole.DOCTOR,
            "department": "General Medicine",
            "is_superuser": False
        },
        {
            "employee_id": "RC0001",
            "email": "reception@hospital.com",
            "password": "Reception@123",
            "full_name": "Priya Nair",
            "role": UserRole.RECEPTIONIST,
            "department": "Front Desk",
            "is_superuser": False
        }
    ]

    created_users = {}

    for u in users:

        user = User(
            employee_id=u["employee_id"],
            email=u["email"],
            hashed_password=get_password_hash(u["password"]),
            full_name=u["full_name"],
            role=u["role"],
            department=u["department"],
            is_active=True,
            is_superuser=u["is_superuser"]
        )

        db.add(user)
        db.flush()

        created_users[u["email"]] = user

    # Doctor Profile
    doctor_user = created_users["doctor@hospital.com"]

    profile = DoctorProfile(
        user_id=doctor_user.id,
        registration_number="TN-MCI-12345",
        specialization="General Medicine",
        qualification="MBBS, MD",
        experience_years=10,
        consultation_fee=500,
        bio="Senior General Physician",
        languages_spoken=["Tamil", "English"],
        available_days=[
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday"
        ],
        consultation_duration_minutes=15
    )

    db.add(profile)
    db.flush()

    # Duty Roster
    for day in [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday"
    ]:

        roster = DutyRoster(
            doctor_id=profile.id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(17, 0),
            max_patients=30
        )

        db.add(roster)

    db.commit()

    print("✅ Users + Doctor Profile seeded")


def seed_patients(db):

    print("\n🚀 Seeding Patients...")

    if db.query(Patient).count() > 0:
        print("✅ Patients already seeded")
        return

    patients = [
        {
            "patient_code": "PAT0001",
            "full_name": "Arun Kumar",
            "gender": "Male",
            "phone": "9876543210",
            "blood_group": "O+"
        },
        {
            "patient_code": "PAT0002",
            "full_name": "Priya Sharma",
            "gender": "Female",
            "phone": "9876543211",
            "blood_group": "A+"
        },
        {
            "patient_code": "PAT0003",
            "full_name": "Karthik Ravi",
            "gender": "Male",
            "phone": "9876543212",
            "blood_group": "B+"
        }
    ]

    for p in patients:
        db.add(Patient(**p))

    db.commit()

    print(f"✅ {len(patients)} patients seeded")


# =========================================================
# PHASE 2
# =========================================================

def seed_wards_and_beds(db):

    print("\n🚀 Seeding Wards & Beds...")

    if db.query(Ward).count() > 0:
        print("✅ Wards already seeded")
        return

    wards_data = [
        {
            "name": "General Ward A",
            "ward_type": WardType.GENERAL,
            "floor": 1,
            "total_beds": 20,
            "charge_per_day": 500
        },
        {
            "name": "Private Ward",
            "ward_type": WardType.PRIVATE,
            "floor": 2,
            "total_beds": 10,
            "charge_per_day": 2000
        },
        {
            "name": "ICU",
            "ward_type": WardType.ICU,
            "floor": 3,
            "total_beds": 8,
            "charge_per_day": 5000
        },
        {
            "name": "Emergency Ward",
            "ward_type": WardType.EMERGENCY,
            "floor": 0,
            "total_beds": 10,
            "charge_per_day": 1500
        }
    ]

    for wd in wards_data:

        ward = Ward(
            **wd,
            available_beds=wd["total_beds"]
        )

        db.add(ward)

    db.flush()

    bed_count = 0

    for ward in db.query(Ward).all():

        prefix = ward.name[:3].upper()

        for i in range(1, ward.total_beds + 1):

            bed = Bed(
                bed_number=f"{prefix}-{i:02d}",
                ward_id=ward.id,
                bed_type="standard",
                status=BedStatus.AVAILABLE
            )

            db.add(bed)
            bed_count += 1

    db.commit()

    print(f"✅ {len(wards_data)} wards seeded")
    print(f"✅ {bed_count} beds seeded")


def seed_lab_tests(db):

    print("\n🚀 Seeding Lab Tests...")

    if db.query(LabTest).count() > 0:
        print("✅ Lab tests already seeded")
        return

    tests = [
        {
            "test_code": "CBC",
            "test_name": "Complete Blood Count",
            "category": LabCategory.HAEMATOLOGY,
            "sample_type": "Blood",
            "normal_range": "WBC: 4-11",
            "unit": "K/uL",
            "price": 200,
            "turnaround_time_hours": 2
        },
        {
            "test_code": "FBS",
            "test_name": "Fasting Blood Sugar",
            "category": LabCategory.BIOCHEMISTRY,
            "sample_type": "Blood",
            "normal_range": "70-100",
            "unit": "mg/dL",
            "price": 60,
            "turnaround_time_hours": 2
        }
    ]

    for t in tests:
        db.add(LabTest(**t))

    db.commit()

    print(f"✅ {len(tests)} lab tests seeded")


def seed_operation_theatres(db):

    print("\n🚀 Seeding OTs...")

    if db.query(OperationTheatre).count() > 0:
        print("✅ OTs already seeded")
        return

    ots = [
        {
            "ot_number": "OT-01",
            "name": "Major OT 1",
            "ot_type": "Major",
            "floor": 3
        },
        {
            "ot_number": "OT-02",
            "name": "Minor OT",
            "ot_type": "Minor",
            "floor": 2
        }
    ]

    for o in ots:

        db.add(
            OperationTheatre(
                **o,
                status=OTStatus.AVAILABLE
            )
        )

    db.commit()

    print(f"✅ {len(ots)} OTs seeded")


# =========================================================
# PHASE 3
# =========================================================

def seed_services(db):

    print("\n🚀 Seeding Services...")

    if db.query(ServiceMaster).count() > 0:
        print("✅ Services already seeded")
        return

    services = [
        {
            "service_code": "OPD_CONS",
            "service_name": "OPD Consultation",
            "category": ServiceCategory.CONSULTATION,
            "unit_price": 500
        },
        {
            "service_code": "MRI",
            "service_name": "MRI Scan",
            "category": ServiceCategory.RADIOLOGY,
            "unit_price": 6000
        }
    ]

    for s in services:
        db.add(ServiceMaster(**s))

    db.commit()

    print(f"✅ {len(services)} services seeded")


def seed_packages(db):

    print("\n🚀 Seeding Billing Packages...")

    if db.query(BillingPackage).count() > 0:
        print("✅ Packages already seeded")
        return

    packages = [
        {
            "package_code": "NVD_PKG",
            "package_name": "Normal Delivery Package",
            "total_price": 15000,
            "validity_days": 5,
            "inclusions": [
                "Room",
                "Nursing",
                "Diet"
            ]
        }
    ]

    for p in packages:
        db.add(BillingPackage(**p))

    db.commit()

    print(f"✅ {len(packages)} packages seeded")


def seed_pharmacy(db):

    print("\n🚀 Seeding Pharmacy...")

    if db.query(DrugMaster).count() > 0:
        print("✅ Drugs already seeded")
        return

    drugs = [
        {
            "drug_code": "PCM500",
            "brand_name": "Crocin 500mg",
            "generic_name": "Paracetamol",
            "category": DrugCategory.ANALGESIC,
            "formulation": DrugFormulation.TABLET,
            "strength": "500mg",
            "unit": "tablet",
            "reorder_level": 100
        }
    ]

    for d in drugs:

        drug = DrugMaster(
            **d,
            tax_percent=12
        )

        db.add(drug)

    db.flush()

    for drug in db.query(DrugMaster).all():

        stock = DrugStock(
            drug_id=drug.id,
            batch_number=f"INIT{drug.drug_code}",
            expiry_date=date.today() + timedelta(days=730),
            quantity_received=500,
            quantity_available=500,
            purchase_price=5,
            sale_price=10,
            mrp=12,
            location="Rack-A"
        )

        db.add(stock)

    db.commit()

    print(f"✅ {len(drugs)} drugs seeded")


def seed_suppliers(db):

    print("\n🚀 Seeding Suppliers...")

    if db.query(PharmacySupplier).count() > 0:
        print("✅ Suppliers already seeded")
        return

    suppliers = [
        {
            "supplier_code": "SUP001",
            "name": "MediCorp Pharmaceuticals",
            "contact_person": "Ramesh Kumar",
            "phone": "9876543210",
            "email": "orders@medicorp.com",
            "payment_terms": "Net 30"
        }
    ]

    for s in suppliers:
        db.add(PharmacySupplier(**s))

    db.commit()

    print(f"✅ {len(suppliers)} suppliers seeded")


def seed_insurance(db):

    print("\n🚀 Seeding Insurance Companies...")

    if db.query(InsuranceCompany).count() > 0:
        print("✅ Insurance already seeded")
        return

    companies = [
        {
            "company_code": "STAR",
            "name": "Star Health Insurance",
            "tpa_name": "Star TPA",
            "phone": "04428288800",
            "email": "care@starhealth.in"
        }
    ]

    for c in companies:
        db.add(InsuranceCompany(**c))

    db.commit()

    print(f"✅ {len(companies)} insurance companies seeded")


# =========================================================
# PHASE 4
# =========================================================

def seed_hr(db):

    print("\n🚀 Seeding HR Masters...")

    if db.query(Department).count() == 0:

        departments = [
            {
                "dept_code": "ADMIN",
                "name": "Administration",
                "description": "Hospital administration"
            },
            {
                "dept_code": "NURSE",
                "name": "Nursing",
                "description": "Patient care"
            },
            {
                "dept_code": "LAB",
                "name": "Laboratory",
                "description": "Lab department"
            }
        ]

        for d in departments:
            db.add(Department(**d))

        db.flush()

        print(f"✅ {len(departments)} departments seeded")

    if db.query(Designation).count() == 0:

        designations = [
            {
                "title": "Staff Nurse",
                "grade": "C",
                "basic_salary_min": 20000,
                "basic_salary_max": 35000,
                "is_active": True
            },
            {
                "title": "Lab Technician",
                "grade": "C",
                "basic_salary_min": 18000,
                "basic_salary_max": 30000,
                "is_active": True
            }
        ]

        for desig in designations:
            db.add(Designation(**desig))

        print(f"✅ {len(designations)} designations seeded")

    if db.query(Holiday).count() == 0:

        holidays = [
            {
                "name": "Pongal",
                "date": date(2026, 1, 14),
                "holiday_type": "national"
            },
            {
                "name": "Republic Day",
                "date": date(2026, 1, 26),
                "holiday_type": "national"
            }
        ]

        for h in holidays:
            db.add(Holiday(**h))

        print(f"✅ {len(holidays)} holidays seeded")

    db.commit()


# =========================================================
# RUN ALL
# =========================================================

def run_all():

    db = SessionLocal()

    try:

        print("\n==============================")
        print("🏥 HMS MASTER SEED STARTED")
        print("==============================")

        # PHASE 1
        seed_users(db)
        seed_patients(db)

        # PHASE 2
        seed_wards_and_beds(db)
        seed_lab_tests(db)
        seed_operation_theatres(db)

        # PHASE 3
        seed_services(db)
        seed_packages(db)
        seed_pharmacy(db)
        seed_suppliers(db)
        seed_insurance(db)

        # PHASE 4
        seed_hr(db)

        print("\n🎉 HMS MASTER SEED COMPLETED")

        print("\n📋 LOGIN CREDENTIALS")
        print("--------------------------------")

        print("Admin:")
        print("  admin@hospital.com / Admin@123")

        print("\nDoctor:")
        print("  doctor@hospital.com / Doctor@123")

        print("\nReception:")
        print("  reception@hospital.com / Reception@123")

    except Exception as e:

        db.rollback()

        print(f"\n❌ ERROR: {e}")

        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    run_all()


# """
# Run after DB is up:
#     docker-compose exec backend python seed_all.py
# """

# import sys
# sys.path.append(".")

# from datetime import date, timedelta, time

# from app.core.database import SessionLocal
# from app.core.security import get_password_hash

# # Users
# from app.models.user import User, UserRole

# # Doctors
# from app.models.doctor import DoctorProfile, DutyRoster

# # IPD
# from app.models.ipd import Ward, Bed, WardType, BedStatus

# # Lab
# from app.models.lab import LabTest, LabCategory

# # OT
# from app.models.ot import OperationTheatre, OTStatus

# # Billing
# from app.models.billing import (
#     ServiceMaster,
#     BillingPackage,
#     ServiceCategory
# )

# # Pharmacy
# from app.models.pharmacy import (
#     DrugMaster,
#     DrugStock,
#     PharmacySupplier,
#     DrugCategory,
#     DrugFormulation
# )

# # Insurance
# from app.models.insurance import InsuranceCompany


# def seed_users(db):
#     print("\n🚀 Seeding Users...")

#     existing = db.query(User).filter(
#         User.email == "admin@hospital.com"
#     ).first()

#     if existing:
#         print("✅ Users already seeded")
#         return

#     # Admin
#     admin = User(
#         employee_id="AD0001",
#         email="admin@hospital.com",
#         hashed_password=get_password_hash("Admin@123"),
#         full_name="System Administrator",
#         role=UserRole.ADMIN,
#         is_active=True,
#         is_superuser=True,
#         department="Administration"
#     )
#     db.add(admin)

#     # Doctor
#     doctor_user = User(
#         employee_id="DR0001",
#         email="doctor@hospital.com",
#         hashed_password=get_password_hash("Doctor@123"),
#         full_name="Dr. Rajesh Kumar",
#         role=UserRole.DOCTOR,
#         is_active=True,
#         department="General Medicine"
#     )
#     db.add(doctor_user)

#     db.flush()

#     # Doctor Profile
#     profile = DoctorProfile(
#         user_id=doctor_user.id,
#         registration_number="TN-MCI-12345",
#         specialization="General Medicine",
#         qualification="MBBS, MD",
#         experience_years=10,
#         consultation_fee=500.0,
#         bio="Experienced general physician with 10+ years in patient care.",
#         languages_spoken=["Tamil", "English", "Hindi"],
#         available_days=[
#             "Monday",
#             "Tuesday",
#             "Wednesday",
#             "Thursday",
#             "Friday"
#         ],
#         consultation_duration_minutes=15
#     )
#     db.add(profile)

#     db.flush()

#     # Duty Roster
#     for day in [
#         "Monday",
#         "Tuesday",
#         "Wednesday",
#         "Thursday",
#         "Friday"
#     ]:
#         roster = DutyRoster(
#             doctor_id=profile.id,
#             day_of_week=day,
#             start_time=time(9, 0),
#             end_time=time(17, 0),
#             max_patients=30
#         )
#         db.add(roster)

#     # Receptionist
#     receptionist = User(
#         employee_id="RC0001",
#         email="reception@hospital.com",
#         hashed_password=get_password_hash("Reception@123"),
#         full_name="Priya Nair",
#         role=UserRole.RECEPTIONIST,
#         is_active=True,
#         department="Front Desk"
#     )
#     db.add(receptionist)

#     db.commit()

#     print("✅ Users seeded")


# def seed_wards_and_beds(db):
#     print("\n🚀 Seeding Wards & Beds...")

#     if db.query(Ward.id).first():
#         print("✅ Wards already seeded")
#         return

#     wards_data = [
#         {
#             "name": "General Ward A",
#             "ward_type": WardType.GENERAL,
#             "floor": 1,
#             "total_beds": 20,
#             "charge_per_day": 500
#         },
#         {
#             "name": "General Ward B",
#             "ward_type": WardType.GENERAL,
#             "floor": 1,
#             "total_beds": 20,
#             "charge_per_day": 500
#         },
#         {
#             "name": "Private Ward",
#             "ward_type": WardType.PRIVATE,
#             "floor": 2,
#             "total_beds": 10,
#             "charge_per_day": 2000
#         },
#         {
#             "name": "Semi-Private Ward",
#             "ward_type": WardType.SEMI_PRIVATE,
#             "floor": 2,
#             "total_beds": 15,
#             "charge_per_day": 1000
#         },
#         {
#             "name": "ICU",
#             "ward_type": WardType.ICU,
#             "floor": 3,
#             "total_beds": 8,
#             "charge_per_day": 5000
#         },
#         {
#             "name": "Emergency Ward",
#             "ward_type": WardType.EMERGENCY,
#             "floor": 0,
#             "total_beds": 10,
#             "charge_per_day": 1500
#         }
#     ]

#     for wd in wards_data:
#         ward = Ward(
#             **wd,
#             available_beds=wd["total_beds"]
#         )
#         db.add(ward)

#     db.flush()

#     bed_count = 0

#     for ward in db.query(Ward).all():

#         prefix = ward.name[:3].upper()

#         for i in range(1, ward.total_beds + 1):

#             bed = Bed(
#                 bed_number=f"{prefix}-{i:02d}",
#                 ward_id=ward.id,
#                 bed_type="standard",
#                 status=BedStatus.AVAILABLE
#             )

#             db.add(bed)
#             bed_count += 1

#     db.commit()

#     print(f"✅ {len(wards_data)} wards seeded")
#     print(f"✅ {bed_count} beds seeded")


# def seed_lab_tests(db):
#     print("\n🚀 Seeding Lab Tests...")

#     if db.query(LabTest.id).first():
#         print("✅ Lab tests already seeded")
#         return

#     lab_tests = [
#         {
#             "test_code": "CBC",
#             "test_name": "Complete Blood Count",
#             "category": LabCategory.HAEMATOLOGY,
#             "sample_type": "Blood (EDTA)",
#             "normal_range": "WBC: 4-11 K/uL",
#             "unit": "K/uL",
#             "price": 200,
#             "turnaround_time_hours": 2
#         },
#         {
#             "test_code": "FBS",
#             "test_name": "Fasting Blood Sugar",
#             "category": LabCategory.BIOCHEMISTRY,
#             "sample_type": "Blood (Fluoride)",
#             "normal_range": "70-100 mg/dL",
#             "unit": "mg/dL",
#             "price": 60,
#             "turnaround_time_hours": 2
#         },
#         {
#             "test_code": "LFT",
#             "test_name": "Liver Function Test",
#             "category": LabCategory.BIOCHEMISTRY,
#             "sample_type": "Blood (Plain)",
#             "normal_range": "ALT: 7-56 U/L",
#             "unit": "U/L",
#             "price": 400,
#             "turnaround_time_hours": 4
#         },
#         {
#             "test_code": "KFT",
#             "test_name": "Kidney Function Test",
#             "category": LabCategory.BIOCHEMISTRY,
#             "sample_type": "Blood (Plain)",
#             "normal_range": "Creatinine: 0.7-1.2 mg/dL",
#             "unit": "mg/dL",
#             "price": 350,
#             "turnaround_time_hours": 4
#         }
#     ]

#     for lt in lab_tests:
#         db.add(LabTest(**lt))

#     db.commit()

#     print(f"✅ {len(lab_tests)} lab tests seeded")


# def seed_operation_theatres(db):
#     print("\n🚀 Seeding Operation Theatres...")

#     if db.query(OperationTheatre.id).first():
#         print("✅ OTs already seeded")
#         return

#     ots = [
#         {
#             "ot_number": "OT-01",
#             "name": "Major OT 1",
#             "ot_type": "Major",
#             "floor": 3
#         },
#         {
#             "ot_number": "OT-02",
#             "name": "Major OT 2",
#             "ot_type": "Major",
#             "floor": 3
#         },
#         {
#             "ot_number": "OT-03",
#             "name": "Minor OT",
#             "ot_type": "Minor",
#             "floor": 2
#         }
#     ]

#     for o in ots:
#         ot = OperationTheatre(
#             **o,
#             status=OTStatus.AVAILABLE
#         )
#         db.add(ot)

#     db.commit()

#     print(f"✅ {len(ots)} OTs seeded")


# def seed_services(db):
#     print("\n🚀 Seeding Services...")

#     if db.query(ServiceMaster.id).first():
#         print("✅ Services already seeded")
#         return

#     services = [
#         {
#             "service_code": "OPD_CONS",
#             "service_name": "OPD Consultation",
#             "category": ServiceCategory.CONSULTATION,
#             "unit_price": 500
#         },
#         {
#             "service_code": "ICU_CHARGE",
#             "service_name": "ICU Bed Charge",
#             "category": ServiceCategory.ROOM_CHARGE,
#             "unit_price": 5000
#         },
#         {
#             "service_code": "MRI",
#             "service_name": "MRI",
#             "category": ServiceCategory.RADIOLOGY,
#             "unit_price": 6000
#         }
#     ]

#     for s in services:
#         db.add(ServiceMaster(**s))

#     db.commit()

#     print(f"✅ {len(services)} services seeded")


# def seed_packages(db):
#     print("\n🚀 Seeding Billing Packages...")

#     if db.query(BillingPackage.id).first():
#         print("✅ Packages already seeded")
#         return

#     packages = [
#         {
#             "package_code": "NVD_PKG",
#             "package_name": "Normal Vaginal Delivery Package",
#             "total_price": 15000,
#             "validity_days": 5,
#             "inclusions": [
#                 "Room charge",
#                 "Nursing",
#                 "Diet"
#             ]
#         },
#         {
#             "package_code": "APPY_PKG",
#             "package_name": "Appendectomy Package",
#             "total_price": 25000,
#             "validity_days": 5,
#             "inclusions": [
#                 "OT charges",
#                 "Nursing"
#             ]
#         }
#     ]

#     for p in packages:
#         db.add(BillingPackage(**p))

#     db.commit()

#     print(f"✅ {len(packages)} packages seeded")


# def seed_pharmacy(db):
#     print("\n🚀 Seeding Pharmacy...")

#     if db.query(DrugMaster.id).first():
#         print("✅ Drugs already seeded")
#         return

#     drugs = [
#         {
#             "drug_code": "PCM500",
#             "brand_name": "Crocin 500mg",
#             "generic_name": "Paracetamol",
#             "category": DrugCategory.ANALGESIC,
#             "formulation": DrugFormulation.TABLET,
#             "strength": "500mg",
#             "unit": "tablet",
#             "reorder_level": 100
#         },
#         {
#             "drug_code": "AMX500",
#             "brand_name": "Amoxil 500mg",
#             "generic_name": "Amoxicillin",
#             "category": DrugCategory.ANTIBIOTIC,
#             "formulation": DrugFormulation.CAPSULE,
#             "strength": "500mg",
#             "unit": "capsule",
#             "reorder_level": 50
#         }
#     ]

#     for d in drugs:
#         drug = DrugMaster(
#             **d,
#             tax_percent=12.0
#         )
#         db.add(drug)

#     db.flush()

#     for drug in db.query(DrugMaster).all():

#         stock = DrugStock(
#             drug_id=drug.id,
#             batch_number=f"INIT{drug.drug_code}001",
#             expiry_date=date.today() + timedelta(days=730),
#             quantity_received=500,
#             quantity_available=500,
#             purchase_price=5.0,
#             sale_price=10.0,
#             mrp=12.0,
#             location="Rack-A"
#         )

#         db.add(stock)

#     db.commit()

#     print(f"✅ {len(drugs)} drugs seeded")


# def seed_suppliers(db):
#     print("\n🚀 Seeding Suppliers...")

#     if db.query(PharmacySupplier.id).first():
#         print("✅ Suppliers already seeded")
#         return

#     suppliers = [
#         {
#             "supplier_code": "SUP001",
#             "name": "MediCorp Pharmaceuticals",
#             "contact_person": "Ramesh Kumar",
#             "phone": "9876543210",
#             "email": "orders@medicorp.com",
#             "payment_terms": "Net 30"
#         }
#     ]

#     for s in suppliers:
#         db.add(PharmacySupplier(**s))

#     db.commit()

#     print(f"✅ {len(suppliers)} suppliers seeded")


# def seed_insurance(db):
#     print("\n🚀 Seeding Insurance Companies...")

#     if db.query(InsuranceCompany.id).first():
#         print("✅ Insurance already seeded")
#         return

#     companies = [
#         {
#             "company_code": "STAR",
#             "name": "Star Health Insurance",
#             "tpa_name": "Star TPA",
#             "phone": "044-28288800",
#             "email": "care@starhealth.in"
#         },
#         {
#             "company_code": "NIVA",
#             "name": "Niva Bupa Health Insurance",
#             "tpa_name": "Vidal Health",
#             "phone": "1800-200-7878",
#             "email": "care@nivabupa.com"
#         }
#     ]

#     for c in companies:
#         db.add(InsuranceCompany(**c))

#     db.commit()

#     print(f"✅ {len(companies)} insurance companies seeded")


# def run_all():
#     db = SessionLocal()

#     try:
#         seed_users(db)
#         seed_wards_and_beds(db)
#         seed_lab_tests(db)
#         seed_operation_theatres(db)
#         seed_services(db)
#         seed_packages(db)
#         seed_pharmacy(db)
#         seed_suppliers(db)
#         seed_insurance(db)

#         print("\n🎉 HMS Master Seed Completed Successfully!")

#         print("\n📋 Login Credentials")
#         print("--------------------------------")
#         print("Admin:")
#         print("  admin@hospital.com / Admin@123")

#         print("\nDoctor:")
#         print("  doctor@hospital.com / Doctor@123")

#         print("\nReception:")
#         print("  reception@hospital.com / Reception@123")

#     except Exception as e:
#         db.rollback()

#         print(f"\n❌ ERROR: {e}")

#         import traceback
#         traceback.print_exc()

#     finally:
#         db.close()


# if __name__ == "__main__":
#     run_all()