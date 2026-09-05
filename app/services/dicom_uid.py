"""
DICOM UID generation using the standard's own "UUID-derived OID" scheme
(DICOM PS3.5, Annex B) — converts a random UUID into a syntactically valid
DICOM UID under the well-known `2.25` root that DICOM itself reserves for
exactly this purpose (no need to register an organizational root just to
generate internally-unique UIDs). This produces globally-unique-enough UIDs
for internal use; swap in a registered organizational root before relying
on these in an external multi-institution DICOM exchange, since `2.25`-based
UIDs are technically unique but not tied to your organization's identity
the way a registered root would be.
"""
import uuid


def generate_dicom_uid() -> str:
    """Returns a DICOM-valid UID string, e.g. '2.25.123456789012345678901234567890123456'"""
    return f"2.25.{uuid.uuid4().int}"


def generate_accession_number(prefix: str = "ACC") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12].upper()}"
