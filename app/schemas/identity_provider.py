from pydantic import BaseModel
from typing import Optional


class OIDCProviderCreate(BaseModel):
    provider_name: str
    issuer: str
    client_id: str
    client_secret: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: Optional[str] = None
    redirect_uri: str
    scopes: str = "openid profile email"


class OIDCProviderResponse(BaseModel):
    id: int
    provider_name: str
    issuer: str
    is_active: bool

    class Config:
        from_attributes = True


class SSOLoginUrlResponse(BaseModel):
    authorization_url: str
    state: str


class SSOTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_link: bool
