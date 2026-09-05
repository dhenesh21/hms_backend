"""
FHIR R4 resource mappers (item 246). Hand-built JSON shapes rather than a
third-party FHIR library (none available to install in this environment) —
each mapper follows the R4 spec's required fields for that resource type.
This is a READ-ONLY facade: internal models are the source of truth,
these functions only reshape existing data into FHIR's wire format for
external consumers. No FHIR resource is ever written back into this system
from here — an inbound FHIR write endpoint is a different, larger piece of
work (validation, conflict resolution) not attempted in this pass.
"""
from typing import Optional


def patient_to_fhir(p) -> dict:
    return {
        "resourceType": "Patient",
        "id": str(p.id),
        "identifier": [{"system": "urn:hms:uhid", "value": p.uhid}],
        "name": [{"family": p.last_name, "given": [p.first_name]}],
        "gender": p.gender.value if p.gender else None,
        "birthDate": p.date_of_birth.isoformat() if p.date_of_birth else None,
        "telecom": [
            t for t in [
                {"system": "phone", "value": p.phone} if p.phone else None,
                {"system": "email", "value": p.email} if p.email else None,
            ] if t
        ],
        "address": [{
            "line": [p.address] if p.address else [],
            "city": p.city, "state": p.state, "postalCode": p.pincode,
        }] if (p.address or p.city) else [],
    }


def practitioner_to_fhir(doc, user) -> dict:
    return {
        "resourceType": "Practitioner",
        "id": str(doc.id),
        "identifier": [{"system": "urn:hms:registration-number", "value": doc.registration_number}],
        "name": [{"text": user.full_name}] if user else [],
        "telecom": [
            t for t in [
                {"system": "phone", "value": user.phone} if user and user.phone else None,
                {"system": "email", "value": user.email} if user and user.email else None,
            ] if t
        ],
        "qualification": [{"code": {"text": doc.qualification}}] if doc.qualification else [],
    }


def appointment_to_fhir_encounter(a) -> dict:
    status_map = {
        "scheduled": "planned", "confirmed": "arrived", "in_progress": "in-progress",
        "completed": "finished", "cancelled": "cancelled", "no_show": "cancelled",
    }
    return {
        "resourceType": "Encounter",
        "id": str(a.id),
        "identifier": [{"system": "urn:hms:appointment-number", "value": a.appointment_number}],
        "status": status_map.get(a.status.value if a.status else "", "unknown"),
        "class": {"code": "AMB", "display": "ambulatory"},
        "type": [{"text": a.appointment_type.value if a.appointment_type else None}],
        "subject": {"reference": f"Patient/{a.patient_id}"},
        "participant": [{"individual": {"reference": f"Practitioner/{a.doctor_id}"}}],
        "period": {"start": f"{a.appointment_date.isoformat()}T{a.appointment_time}:00"} if a.appointment_date else None,
        "reasonCode": [{"text": a.reason}] if a.reason else [],
    }


def lab_result_to_fhir_observation(item, test, order) -> dict:
    status_map = {"normal": "final", "high": "final", "low": "final", "critical": "final"}
    return {
        "resourceType": "Observation",
        "id": str(item.id),
        "status": status_map.get(item.result_status, "preliminary") if item.result_status else "registered",
        "code": {"text": test.test_name} if test else None,
        "subject": {"reference": f"Patient/{order.patient_id}"} if order else None,
        "effectiveDateTime": item.result_entered_at.isoformat() if item.result_entered_at else None,
        "valueString": item.result_value if item.result_value else None,
        "valueQuantity": {"value": item.result_numeric} if item.result_numeric is not None else None,
        "interpretation": [{"text": item.result_status}] if item.result_status else [],
    }


def allergy_to_fhir(a) -> dict:
    severity_map = {"mild": "mild", "moderate": "moderate", "severe": "severe"}
    return {
        "resourceType": "AllergyIntolerance",
        "id": str(a.id),
        "clinicalStatus": {"text": "active" if a.is_active else "inactive"},
        "code": {"text": a.allergen},
        "patient": {"reference": f"Patient/{a.patient_id}"},
        "reaction": [{"manifestation": [{"text": a.reaction}], "severity": severity_map.get(a.severity.value if a.severity else "", None)}] if a.reaction else [],
    }


def condition_to_fhir(c) -> dict:
    return {
        "resourceType": "Condition",
        "id": str(c.id),
        "clinicalStatus": {"text": c.current_status or ("active" if c.is_active else "resolved")},
        "code": {"text": c.condition_name, "coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": c.icd_code}] if c.icd_code else []},
        "subject": {"reference": f"Patient/{c.patient_id}"},
        "onsetDateTime": c.diagnosed_date.isoformat() if c.diagnosed_date else None,
    }


def claim_to_fhir(claim, company=None) -> dict:
    """
    Item 251 (Insurance APIs) as an international standard rather than a
    specific insurer's proprietary API — FHIR's Claim resource is the
    globally standard shape for exchanging claim data, used by payers in
    the US, Australia, and elsewhere. This maps this system's existing
    InsuranceClaim (already comprehensive — preauth, ICD/procedure codes,
    amounts, settlement) into that standard shape. A specific insurer would
    still need connecting (their own submission endpoint, auth) — that part
    stays genuinely vendor-specific (Batch C) — but the DATA SHAPE this
    produces is not proprietary to any one of them.
    """
    status_map = {"draft": "draft", "submitted": "active", "approved": "active",
                  "settled": "active", "rejected": "cancelled"}
    return {
        "resourceType": "Claim",
        "id": str(claim.id),
        "identifier": [{"system": "urn:hms:claim-number", "value": claim.claim_number}],
        "status": status_map.get(claim.status.value if claim.status else "", "draft"),
        "type": {"text": "institutional"},
        "patient": {"reference": f"Patient/{claim.patient_id}"},
        "created": claim.created_at.isoformat() if claim.created_at else None,
        "diagnosis": [
            {"sequence": i + 1, "diagnosisCodeableConcept": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": code}]}}
            for i, code in enumerate(claim.icd_codes or [])
        ],
        "procedure": [
            {"sequence": i + 1, "procedureCodeableConcept": {"text": code}}
            for i, code in enumerate(claim.procedure_codes or [])
        ],
        "total": {"value": claim.claimed_amount, "currency": "INR"},
        "insurance": [{"sequence": 1, "focal": True, "coverage": {"display": company.name if company else None}}] if company else [],
    }


def payment_to_fhir_paymentnotice(payment) -> dict:
    """
    Item 252 (Payment APIs) as an international standard resource
    (PaymentNotice) rather than a specific gateway's webhook/callback
    shape — this represents a payment that already happened in this
    system, in a vendor-neutral format. Actually TAKING a payment still
    needs a real gateway integration (see services/payment_gateway.py's
    pluggable interface) — this mapper is the output-side standard shape,
    not a replacement for that.
    """
    return {
        "resourceType": "PaymentNotice",
        "id": str(payment.id),
        "identifier": [{"system": "urn:hms:payment-number", "value": payment.payment_number}],
        "status": "active",
        "payment": {"display": payment.transaction_reference} if payment.transaction_reference else None,
        "created": payment.payment_date.isoformat() if payment.payment_date else None,
        "payee": {"display": "HMS Hospital"},
        "amount": {"value": payment.amount, "currency": "INR"},
        "paymentStatus": {"text": "paid"},
    }
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": "2026-08-26",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "implementation": {"url": base_url},
        "rest": [{
            "mode": "server",
            "resource": [
                {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                {"type": "Practitioner", "interaction": [{"code": "read"}]},
                {"type": "Encounter", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                {"type": "Observation", "interaction": [{"code": "search-type"}]},
                {"type": "AllergyIntolerance", "interaction": [{"code": "search-type"}]},
                {"type": "Condition", "interaction": [{"code": "search-type"}]},
                {"type": "Claim", "interaction": [{"code": "read"}]},
                {"type": "PaymentNotice", "interaction": [{"code": "read"}]},
            ],
        }],
    }
