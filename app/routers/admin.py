from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Date
from typing import Optional
from datetime import datetime, date
from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash
from app.models.user import User
from app.models.admin import (Role, Permission, RolePermission, UserRoleAssignment,
                               AuditLog, SystemSetting, LoginHistory)
from app.schemas.admin import (
    RoleCreate, RoleResponse,
    PermissionCreate, PermissionResponse,
    RolePermissionUpdate, AssignRoleRequest, UserRoleAssignmentResponse,
    AuditLogResponse, SystemSettingCreate, SystemSettingUpdate, SystemSettingResponse,
    LoginHistoryResponse, UserWithRolesResponse
)

router = APIRouter(prefix="/admin", tags=["Admin & RBAC"])


# ── USER MANAGEMENT ───────────────────────────────────
@router.get("/users", response_model=list[UserWithRolesResponse])
async def list_users(search: Optional[str] = Query(None),
                     role: Optional[str] = Query(None),
                     is_active: Optional[bool] = Query(None),
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    q = db.query(User)
    if search:
        q = q.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.employee_id.ilike(f"%{search}%"))
        )
    if role:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)

    users = q.order_by(User.full_name).all()
    result = []
    for u in users:
        user_roles = db.query(UserRoleAssignment).filter(UserRoleAssignment.user_id == u.id, UserRoleAssignment.is_active == True).all()
        role_names = []
        for ur in user_roles:
            r = db.query(Role).filter(Role.id == ur.role_id).first()
            if r:
                role_names.append(r.display_name)
        result.append(UserWithRolesResponse(
            id=u.id, employee_id=u.employee_id, email=u.email,
            full_name=u.full_name, role=u.role.value if hasattr(u.role, 'value') else str(u.role),
            department=u.department, is_active=u.is_active,
            last_login=u.last_login, assigned_roles=role_names
        ))
    return result


@router.put("/users/{user_id}/toggle-status")
async def toggle_user_status(user_id: int,
                              db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = not user.is_active
    _log_audit(db, current_user.id, "TOGGLE_USER_STATUS",
               "users", str(user_id), {"is_active": user.is_active})
    db.commit()
    return {"message": f"User {'activated' if user.is_active else 'deactivated'}", "is_active": user.is_active}


@router.put("/users/{user_id}/reset-password")
async def reset_password(user_id: int, new_password: str,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(new_password)
    _log_audit(db, current_user.id, "RESET_PASSWORD", "users", str(user_id))
    db.commit()
    return {"message": "Password reset successfully"}


@router.get("/users/{user_id}/login-history", response_model=list[LoginHistoryResponse])
async def get_login_history(user_id: int,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    return db.query(LoginHistory).filter(
        LoginHistory.user_id == user_id
    ).order_by(LoginHistory.login_at.desc()).limit(50).all()


# ── ROLES ─────────────────────────────────────────────
@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_role(data: RoleCreate,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    if db.query(Role).filter(Role.name == data.name).first():
        raise HTTPException(status_code=400, detail="Role name already exists")
    role = Role(**data.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    return db.query(Role).filter(Role.is_active == True).all()


@router.delete("/roles/{role_id}")
async def delete_role(role_id: int,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    role.is_active = False
    db.commit()
    return {"message": "Role deleted"}


# ── PERMISSIONS ───────────────────────────────────────
@router.post("/permissions", response_model=PermissionResponse, status_code=201)
async def create_permission(data: PermissionCreate,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    perm = Permission(**data.model_dump())
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(module: Optional[str] = Query(None),
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    q = db.query(Permission)
    if module:
        q = q.filter(Permission.module == module)
    return q.order_by(Permission.module, Permission.resource).all()


@router.get("/roles/{role_id}/permissions")
async def get_role_permissions(role_id: int,
                                db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    rps = db.query(RolePermission).filter(RolePermission.role_id == role_id, RolePermission.granted == True).all()
    perm_ids = [rp.permission_id for rp in rps]
    perms = db.query(Permission).filter(Permission.id.in_(perm_ids)).all()
    all_perms = db.query(Permission).all()
    return {
        "role": {"id": role.id, "name": role.name, "display_name": role.display_name},
        "granted_permissions": [{"id": p.id, "module": p.module, "resource": p.resource, "action": p.action} for p in perms],
        "all_permissions": [{"id": p.id, "module": p.module, "resource": p.resource, "action": p.action} for p in all_perms],
    }


@router.put("/roles/{role_id}/permissions")
async def update_role_permissions(role_id: int, data: RolePermissionUpdate,
                                   db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_user)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    # Remove old permissions
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    # Add new
    for perm_id in data.permission_ids:
        rp = RolePermission(role_id=role_id, permission_id=perm_id, granted=data.granted)
        db.add(rp)
    _log_audit(db, current_user.id, "UPDATE_ROLE_PERMISSIONS", "roles", str(role_id))
    db.commit()
    return {"message": f"Updated {len(data.permission_ids)} permissions for role"}


# ── ASSIGN ROLES TO USERS ─────────────────────────────
@router.post("/users/assign-role")
async def assign_role(data: AssignRoleRequest,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    existing = db.query(UserRoleAssignment).filter(
        UserRoleAssignment.user_id == data.user_id,
        UserRoleAssignment.role_id == data.role_id,
        UserRoleAssignment.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role already assigned to user")
    ur = UserRoleAssignment(user_id=data.user_id, role_id=data.role_id,
                  assigned_by=current_user.id, expires_at=data.expires_at)
    db.add(ur)
    _log_audit(db, current_user.id, "ASSIGN_ROLE", "users", str(data.user_id),
               {"role_id": data.role_id, "role_name": role.name})
    db.commit()
    return {"message": f"Role '{role.display_name}' assigned to user"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def revoke_role(user_id: int, role_id: int,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    ur = db.query(UserRoleAssignment).filter(UserRoleAssignment.user_id == user_id, UserRoleAssignment.role_id == role_id).first()
    if not ur:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    ur.is_active = False
    db.commit()
    return {"message": "Role revoked"}


# ── AUDIT LOGS ────────────────────────────────────────
def _log_audit(db: Session, user_id: int, action: str, resource: str = None,
               resource_id: str = None, new_values: dict = None):
    log = AuditLog(user_id=user_id, action=action, module=resource,
                   resource=resource, resource_id=resource_id,
                   new_values=new_values, status="success")
    db.add(log)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(user_id: Optional[int] = Query(None),
                          module: Optional[str] = Query(None),
                          action: Optional[str] = Query(None),
                          start_date: Optional[date] = Query(None),
                          end_date: Optional[date] = Query(None),
                          limit: int = Query(100, le=500),
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    q = db.query(AuditLog)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if module:
        q = q.filter(AuditLog.module == module)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if start_date:
        q = q.filter(func.cast(AuditLog.created_at, Date) >= start_date)
    if end_date:
        q = q.filter(func.cast(AuditLog.created_at, Date) <= end_date)
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()


# ── SYSTEM SETTINGS ───────────────────────────────────
@router.post("/settings", response_model=SystemSettingResponse, status_code=201)
async def create_setting(data: SystemSettingCreate,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    if db.query(SystemSetting).filter(SystemSetting.key == data.key).first():
        raise HTTPException(status_code=400, detail="Setting key already exists")
    setting = SystemSetting(**data.model_dump(), updated_by=current_user.id)
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


@router.get("/settings", response_model=list[SystemSettingResponse])
async def list_settings(category: Optional[str] = Query(None),
                         db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    q = db.query(SystemSetting)
    if category:
        q = q.filter(SystemSetting.category == category)
    return q.order_by(SystemSetting.category, SystemSetting.key).all()


@router.put("/settings/{key}", response_model=SystemSettingResponse)
async def update_setting(key: str, data: SystemSettingUpdate,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    old_val = setting.value
    setting.value = data.value
    setting.updated_by = current_user.id
    _log_audit(db, current_user.id, "UPDATE_SETTING", "settings", key,
               {"old": old_val, "new": data.value})
    db.commit()
    db.refresh(setting)
    return setting


# ── DASHBOARD ─────────────────────────────────────────
@router.get("/dashboard/stats")
async def admin_stats(db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_roles = db.query(Role).filter(Role.is_active == True).count()
    total_perms = db.query(Permission).count()
    recent_logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(5).all()
    from datetime import date
    today_logins = db.query(LoginHistory).filter(
        func.cast(LoginHistory.login_at, Date) == date.today(),
        LoginHistory.status == "success"
    ).count()
    by_role = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "total_roles": total_roles,
        "total_permissions": total_perms,
        "today_logins": today_logins,
        "users_by_role": {str(r): c for r, c in by_role},
        "recent_audit": [{"action": l.action, "module": l.module, "created_at": l.created_at} for l in recent_logs],
    }





