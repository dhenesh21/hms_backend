from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.security import get_current_user, create_access_token, require_roles
from app.core.config import settings
from app.models.identity_provider import OIDCProviderConfig, SSOIdentityLink
from app.models.user import User, UserRole
from app.schemas.identity_provider import (
    OIDCProviderCreate, OIDCProviderResponse, SSOLoginUrlResponse, SSOTokenResponse,
)

router = APIRouter(prefix="/identity-provider", tags=["Identity Provider (SSO)"])


def _make_state(provider_id: int) -> str:
    """Signed, short-lived JWT used as OAuth `state` — carries the provider_id
    through the redirect round-trip without needing a server-side session
    store; the existing JWT secret/signing already used for auth tokens
    covers CSRF-protection here too (an attacker can't forge a valid state
    without the same secret an attacker also can't forge a valid access
    token with)."""
    payload = {"provider_id": provider_id, "exp": datetime.utcnow() + timedelta(minutes=10), "type": "oidc_state"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _read_state(state: str) -> int:
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired SSO state")
    if payload.get("type") != "oidc_state":
        raise HTTPException(status_code=400, detail="Invalid state token")
    return payload["provider_id"]


# ── PROVIDER CONFIG (admin) ─────────────────────────────
@router.post("/providers", response_model=OIDCProviderResponse, status_code=201)
async def create_provider(data: OIDCProviderCreate, db: Session = Depends(get_db),
                           current_user: User = Depends(require_roles(UserRole.ADMIN))):
    provider = OIDCProviderConfig(**data.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.get("/providers", response_model=List[OIDCProviderResponse])
async def list_providers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(OIDCProviderConfig).filter(OIDCProviderConfig.is_active == True).all()


# ── SSO LOGIN FLOW ───────────────────────────────────────
@router.get("/{provider_id}/login", response_model=SSOLoginUrlResponse)
async def get_login_url(provider_id: int, db: Session = Depends(get_db)):
    """No auth required — this IS the login entry point. Frontend redirects
    the browser to `authorization_url`."""
    provider = db.query(OIDCProviderConfig).filter(
        OIDCProviderConfig.id == provider_id, OIDCProviderConfig.is_active == True).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found or inactive")

    state = _make_state(provider_id)
    params = {
        "client_id": provider.client_id, "redirect_uri": provider.redirect_uri,
        "response_type": "code", "scope": provider.scopes, "state": state,
    }
    return SSOLoginUrlResponse(authorization_url=f"{provider.authorization_endpoint}?{urlencode(params)}", state=state)


@router.get("/callback", response_model=SSOTokenResponse)
async def sso_callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Exchanges the authorization code for tokens, fetches the user's profile,
    and either links to an existing local User (matched by email) or fails
    with a clear error — this does NOT auto-create new staff accounts from
    an external IdP, since that would let anyone who can authenticate at the
    IdP gain access to this system; provisioning new staff stays an explicit
    admin action (existing POST /auth/register or similar), SSO here only
    covers login for accounts that already exist.
    """
    provider_id = _read_state(state)
    provider = db.query(OIDCProviderConfig).filter(OIDCProviderConfig.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")

    async with httpx.AsyncClient(timeout=10) as client:
        token_res = await client.post(provider.token_endpoint, data={
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": provider.redirect_uri,
            "client_id": provider.client_id, "client_secret": provider.client_secret,
        })
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code with identity provider")
        id_token_data = token_res.json()
        access_token_external = id_token_data.get("access_token")

        userinfo = {}
        if provider.userinfo_endpoint and access_token_external:
            userinfo_res = await client.get(provider.userinfo_endpoint,
                                             headers={"Authorization": f"Bearer {access_token_external}"})
            if userinfo_res.status_code == 200:
                userinfo = userinfo_res.json()

    external_sub = userinfo.get("sub")
    external_email = userinfo.get("email")
    if not external_sub:
        raise HTTPException(status_code=400, detail="Identity provider did not return a subject identifier")

    link = db.query(SSOIdentityLink).filter(
        SSOIdentityLink.provider_id == provider_id, SSOIdentityLink.external_subject_id == external_sub
    ).first()
    is_new_link = False

    if link:
        user = db.query(User).filter(User.id == link.user_id).first()
    else:
        if not external_email:
            raise HTTPException(status_code=400, detail="No existing SSO link and identity provider did not return an email to match against")
        user = db.query(User).filter(User.email == external_email).first()
        if not user:
            raise HTTPException(status_code=403,
                                 detail="No local account matches this identity — an admin must create the staff account before SSO login works for it")
        link = SSOIdentityLink(user_id=user.id, provider_id=provider_id, external_subject_id=external_sub)
        db.add(link)
        is_new_link = True

    link.last_login_at = datetime.now(timezone.utc)
    db.commit()

    local_token = create_access_token({"sub": str(user.id)})
    return SSOTokenResponse(access_token=local_token, is_new_link=is_new_link)
