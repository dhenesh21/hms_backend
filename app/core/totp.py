import base64
import io

import pyotp
import qrcode

from app.core.config import settings


def generate_totp_secret() -> str:
    """Generates a new random base32 TOTP secret (pyotp standard)."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    """otpauth:// URI an authenticator app can scan or import directly."""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email, issuer_name=settings.APP_NAME
    )


def get_qr_code_base64(uri: str) -> str:
    """Renders the otpauth URI as a QR code PNG, returned as a base64
    data URI the frontend can drop straight into an <img> tag."""
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def verify_totp_code(secret: str, code: str) -> bool:
    """Verifies a 6-digit TOTP code against the secret, allowing a small
    window (1 step = 30s) either side for clock drift."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
