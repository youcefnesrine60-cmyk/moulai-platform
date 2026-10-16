# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 RBAC MODELS
# نماذج التحكم في الوصول المبني على الأدوار
# يدير الأدوار والصلاحيات وربطها بالمديرين
# ==============================================

"""Normalized SQLAlchemy models for role-based administrative access control."""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base, BaseModel

# ==============================================
# 🔗 ROLE PERMISSIONS ASSOCIATION
# جدول الربط بين الأدوار والصلاحيات
# ==============================================

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        comment="معرف الدور",
    ),
    Column(
        "permission_id",
        Integer,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
        comment="معرف الصلاحية",
    ),
)

# ==============================================
# 🎭 ROLE
# نموذج الدور - مجموعة صلاحيات إدارية
# ==============================================

class Role(BaseModel):
    """
    نموذج الدور - مجموعة صلاحيات إدارية معرّفة.

    يمثل دوراً إدارياً في النظام مع مجموعة من الصلاحيات
    المرتبطة به، ويمكن ربط عدة مديرين بهذا الدور.

    Attributes:
        code: رمز الدور الفريد (مثال: admin, support).
        name: الاسم الظاهر للدور.
        description: وصف اختياري للدور.
        is_active: حالة تفعيل الدور.
        permissions: قائمة الصلاحيات المرتبطة بالدور.
        admins: قائمة المديرين المرتبطين بهذا الدور.
    """
    __tablename__ = "roles"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    code = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="رمز الدور الفريد",
    )
    name = Column(
        String(128),
        nullable=False,
        comment="الاسم الظاهر للدور",
    )
    description = Column(
        Text,
        nullable=True,
        comment="وصف الدور",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="حالة تفعيل الدور",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
        # comment="الصلاحيات المرتبطة بالدور",
    )
    admins = relationship(
        "Admin",
        back_populates="role_record",
        lazy="selectin",
        # comment="المديرون المرتبطون بهذا الدور",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج.

        Returns:
            سلسلة نصية تحتوي على المعرف والرمز والاسم.
        """
        return (
            f"<Role(id={self.id}, code={self.code}, name={self.name})>"
        )


# ==============================================
# 🔑 PERMISSION
# نموذج الصلاحية - قدرة تفويض ذرية
# ==============================================

class Permission(BaseModel):
    """
    نموذج الصلاحية - قدرة تفويض ذرية معرّفة برمز ثابت.

    تمثل صلاحية واحدة يمكن منحها لدور أو أكثر،
    ويتم تعريفها برمز فريد مستقر.

    Attributes:
        code: رمز الصلاحية الفريد (مثال: orders.read).
        name: الاسم الظاهر للصلاحية.
        description: وصف اختياري للصلاحية.
        roles: قائمة الأدوار المرتبطة بهذه الصلاحية.
    """
    __tablename__ = "permissions"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    code = Column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="رمز الصلاحية الفريد",
    )
    name = Column(
        String(128),
        nullable=False,
        comment="الاسم الظاهر للصلاحية",
    )
    description = Column(
        Text,
        nullable=True,
        comment="وصف الصلاحية",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin",
        # comment="الأدوار المرتبطة بهذه الصلاحية",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج.

        Returns:
            سلسلة نصية تحتوي على المعرف والرمز والاسم.
        """
        return (
            f"<Permission(id={self.id}, code={self.code}, name={self.name})>"
        )


# ==============================================
# 📤 EXPORTS
# ==============================================

__all__ = [
    "Permission",
    "Role",
    "role_permissions",
]