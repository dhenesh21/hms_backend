from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Text, Boolean, Enum, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class PermissionAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    EXPORT = "export"


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)

    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    permissions = relationship(
        "RolePermission",
        back_populates="role"
    )


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)

    module = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)

    action = Column(Enum(PermissionAction), nullable=False)

    display_name = Column(String(200))
    description = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)

    granted = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    role = relationship(
        "Role",
        back_populates="permissions"
    )

    permission = relationship("Permission")


class UserRoleAssignment(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    assigned_by = Column(Integer, ForeignKey("users.id"))

    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    is_active = Column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs_admin"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    session_id = Column(String(100))

    action = Column(String(200), nullable=False)

    module = Column(String(100))
    resource = Column(String(100))
    resource_id = Column(String(50))

    old_values = Column(JSON)
    new_values = Column(JSON)

    ip_address = Column(String(45))
    user_agent = Column(String(500))

    status = Column(String(20), default="success")

    error_message = Column(Text)

    duration_ms = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship(
        "User",
        back_populates="admin_audit_logs"
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    key = Column(String(200), unique=True, nullable=False, index=True)

    value = Column(Text)

    value_type = Column(String(20), default="string")

    category = Column(String(100))

    display_name = Column(String(300))

    description = Column(Text)

    is_public = Column(Boolean, default=False)

    updated_by = Column(Integer, ForeignKey("users.id"))

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    ip_address = Column(String(45))
    user_agent = Column(String(500))

    status = Column(String(20))

    failure_reason = Column(String(200))

    login_at = Column(DateTime(timezone=True), server_default=func.now())

    logout_at = Column(DateTime(timezone=True))

    session_duration_minutes = Column(Integer)

# from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
#                         Text, Float, Boolean, Enum, Date, JSON)
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func
# import enum
# from app.core.database import Base


# class PermissionAction(str, enum.Enum):
#     CREATE = "create"
#     READ = "read"
#     UPDATE = "update"
#     DELETE = "delete"
#     APPROVE = "approve"
#     EXPORT = "export"


# class Role(Base):
#     __tablename__ = "roles"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), unique=True, nullable=False)
#     display_name = Column(String(200), nullable=False)
#     description = Column(Text)
#     is_system = Column(Boolean, default=False)   # built-in roles can't be deleted
#     is_active = Column(Boolean, default=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())

#     permissions = relationship("RolePermission", back_populates="role")


# class Permission(Base):
#     __tablename__ = "permissions"

#     id = Column(Integer, primary_key=True, index=True)
#     module = Column(String(100), nullable=False)     # patients, billing, pharmacy etc
#     resource = Column(String(100), nullable=False)   # patient_list, bill_create etc
#     action = Column(Enum(PermissionAction), nullable=False)
#     display_name = Column(String(200))
#     description = Column(Text)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())


# class RolePermission(Base):
#     __tablename__ = "role_permissions"

#     id = Column(Integer, primary_key=True, index=True)
#     role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
#     permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
#     granted = Column(Boolean, default=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())

#     role = relationship("Role", back_populates="permissions")
#     permission = relationship("Permission")


# class UserRoleAssignment(Base):
#     __tablename__ = "user_roles"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
#     assigned_by = Column(Integer, ForeignKey("users.id"))
#     assigned_at = Column(DateTime(timezone=True), server_default=func.now())
#     expires_at = Column(DateTime(timezone=True))
#     is_active = Column(Boolean, default=True)


# class AuditLog(Base):
#     __tablename__ = "audit_logs_admin"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
#     session_id = Column(String(100))
#     action = Column(String(200), nullable=False)
#     module = Column(String(100))
#     resource = Column(String(100))
#     resource_id = Column(String(50))
#     old_values = Column(JSON)
#     new_values = Column(JSON)
#     ip_address = Column(String(45))
#     user_agent = Column(String(500))
#     status = Column(String(20), default="success")  # success, failed, error
#     error_message = Column(Text)
#     duration_ms = Column(Integer)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     user = relationship("User", back_populates="audit_logs")

# class SystemSetting(Base):
#     __tablename__ = "system_settings"

#     id = Column(Integer, primary_key=True, index=True)
#     key = Column(String(200), unique=True, nullable=False, index=True)
#     value = Column(Text)
#     value_type = Column(String(20), default="string")  # string, int, bool, json
#     category = Column(String(100))   # general, billing, pharmacy, notifications
#     display_name = Column(String(300))
#     description = Column(Text)
#     is_public = Column(Boolean, default=False)
#     updated_by = Column(Integer, ForeignKey("users.id"))
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#     created_at = Column(DateTime(timezone=True), server_default=func.now())



# class LoginHistory(Base):
#     __tablename__ = "login_history"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     ip_address = Column(String(45))
#     user_agent = Column(String(500))
#     status = Column(String(20))   # success, failed, blocked
#     failure_reason = Column(String(200))
#     login_at = Column(DateTime(timezone=True), server_default=func.now())
#     logout_at = Column(DateTime(timezone=True))
#     session_duration_minutes = Column(Integer)


