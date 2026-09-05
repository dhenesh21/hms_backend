"""
HL7 v2.x message generation (item 245) — standard pipe-delimited ADT/ORU
messages, hand-built (no `python-hl7` or similar library installed in this
environment). This generates well-formed HL7 v2 text; it does NOT send it
anywhere — actually delivering a message needs an MLLP connection to a
specific receiving system (a lab, an insurer, a regional HIE), which is
exactly the "needs a specific integration target" situation flagged for
Batch C. What's built here is the message-construction layer any of those
integrations would need regardless of which partner ends up on the other
end — segment structure, field escaping, and the common trigger events
(ADT^A01 admit, ADT^A03 discharge, ADT^A08 update, ORU^R01 lab result).
"""
from datetime import datetime


def _hl7_datetime(dt) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y%m%d%H%M%S")


def _hl7_date(d) -> str:
    if not d:
        return ""
    return d.strftime("%Y%m%d")


def _esc(value) -> str:
    """Escape HL7 field-delimiter-reserved characters."""
    if value is None:
        return ""
    s = str(value)
    return s.replace("|", "\\F\\").replace("^", "\\S\\").replace("~", "\\R\\").replace("&", "\\T\\")


def build_msh(message_type: str, control_id: str, sending_facility: str = "HMS") -> str:
    now = _hl7_datetime(datetime.utcnow())
    return f"MSH|^~\\&|HMS|{sending_facility}|RECEIVING_APP|RECEIVING_FACILITY|{now}||{message_type}|{control_id}|P|2.5"


def build_pid(patient) -> str:
    dob = _hl7_date(patient.date_of_birth)
    gender_map = {"male": "M", "female": "F", "other": "O"}
    gender = gender_map.get(patient.gender.value if patient.gender else "", "U")
    return (f"PID|1||{_esc(patient.uhid)}^^^HMS^MR||"
            f"{_esc(patient.last_name)}^{_esc(patient.first_name)}||{dob}|{gender}|||"
            f"{_esc(patient.address or '')}^^{_esc(patient.city or '')}^{_esc(patient.state or '')}^{_esc(patient.pincode or '')}||"
            f"{_esc(patient.phone)}")


def build_pv1(admission, ward_name: str = "", bed_label: str = "") -> str:
    class_map = {"admitted": "I", "discharged": "I"}
    patient_class = class_map.get(getattr(admission.status, "value", ""), "I")
    return f"PV1|1|{patient_class}|{_esc(ward_name)}^{_esc(bed_label)}||||||||||||||{admission.id}"


def build_adt_a01(patient, admission, ward_name: str = "", bed_label: str = "") -> str:
    """Admit/visit notification."""
    control_id = f"A01{admission.id}"
    return "\r".join([
        build_msh("ADT^A01", control_id),
        build_pid(patient),
        build_pv1(admission, ward_name, bed_label),
    ])


def build_adt_a03(patient, admission, ward_name: str = "", bed_label: str = "") -> str:
    """Discharge notification."""
    control_id = f"A03{admission.id}"
    return "\r".join([
        build_msh("ADT^A03", control_id),
        build_pid(patient),
        build_pv1(admission, ward_name, bed_label),
    ])


def build_adt_a08(patient, admission, ward_name: str = "", bed_label: str = "") -> str:
    """Update patient information."""
    control_id = f"A08{admission.id}"
    return "\r".join([
        build_msh("ADT^A08", control_id),
        build_pid(patient),
        build_pv1(admission, ward_name, bed_label),
    ])


def build_oru_r01(patient, order, test, item) -> str:
    """Lab result message."""
    control_id = f"ORU{item.id}"
    obx = (f"OBX|1|ST|{_esc(test.test_name)}||{_esc(item.result_value or item.result_numeric)}||"
           f"|{_esc(item.result_status or '')}|||F")
    obr = f"OBR|1|{_esc(order.order_number)}||{_esc(test.test_name)}"
    return "\r".join([
        build_msh("ORU^R01", control_id),
        build_pid(patient),
        obr,
        obx,
    ])
