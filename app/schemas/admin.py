from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime
from app.models.admin import PermissionAction


class RoleCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_system: bool
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    module: str
    resource: str
    action: PermissionAction
    display_name: Optional[str] = None
    description: Optional[str] = None


class PermissionResponse(BaseModel):
    id: int
    module: str
    resource: str
    action: PermissionAction
    display_name: Optional[str]
    description: Optional[str]
    class Config:
        from_attributes = True


class RolePermissionUpdate(BaseModel):
    permission_ids: List[int]
    granted: bool = True


class AssignRoleRequest(BaseModel):
    user_id: int
    role_id: int
    expires_at: Optional[datetime] = None


class UserRoleAssignmentResponse(BaseModel):
    id: int
    user_id: int
    role_id: int
    assigned_at: datetime
    is_active: bool
    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    module: Optional[str]
    resource: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    status: str
    created_at: datetime
    class Config:
        from_attributes = True


class SystemSettingCreate(BaseModel):
    key: str
    value: str
    value_type: str = "string"
    category: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = False


class SystemSettingUpdate(BaseModel):
    value: str


class SystemSettingResponse(BaseModel):
    id: int
    key: str
    value: Optional[str]
    value_type: str
    category: Optional[str]
    display_name: Optional[str]
    description: Optional[str]
    is_public: bool
    updated_at: Optional[datetime]
    class Config:
        from_attributes = True


class LoginHistoryResponse(BaseModel):
    id: int
    user_id: int
    ip_address: Optional[str]
    status: str
    login_at: datetime
    logout_at: Optional[datetime]
    session_duration_minutes: Optional[int]
    class Config:
        from_attributes = True


class UserWithRolesResponse(BaseModel):
    id: int
    employee_id: str
    email: str
    full_name: str
    role: str
    department: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    assigned_roles: List[str] = []

