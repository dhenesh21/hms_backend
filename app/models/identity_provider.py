from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from app.core.database import Base


class OIDCProviderConfig(Base):
    """
    Item 254 — a generic OpenID Connect client configuration, not a
    connection to any specific identity provider. OIDC is a protocol
    standard (RFC-level, not a vendor product), so the endpoints and flow
    below can legitimately be built without picking Okta/Azure AD/Google
    Workspace/etc first — same reasoning as FHIR/HL7 being standards rather
    than vendor integrations. WHICH IdP a hospital actually points this at
    (and getting a client_id/secret from that IdP's admin console) is still
    their call — this is the client-side plumbing that works with any
    standards-compliant IdP once those values are filled in.
    """
    __tablename__ = "oidc_provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String(100), nullable=False)     # display name, e.g. "Hospital Group SSO"
    issuer = Column(String(500), nullable=False)
    client_id = Column(String(300), nullable=False)
    client_secret = Column(String(500), nullable=False)     # NOTE: plaintext column — see routers/identity_provider.py docstring
    authorization_endpoint = Column(String(500), nullable=False)
    token_endpoint = Column(String(500), nullable=False)
    userinfo_endpoint = Column(String(500), nullable=True)
    redirect_uri = Column(String(500), nullable=False)
    scopes = Column(String(300), default="openid profile email")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SSOIdentityLink(Base):
    """Links a local staff User to their external identity at a specific
    OIDC provider — one user can have links to multiple providers."""
    __tablename__ = "sso_identity_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("oidc_provider_configs.id"), nullable=False)
    external_subject_id = Column(String(300), nullable=False)   # the 'sub' claim from the IdP
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
