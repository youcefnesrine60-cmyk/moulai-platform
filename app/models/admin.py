# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 ADMIN MODEL
# نموذج المدير - صلاحيات الإدارة والتحكم
# يدير بيانات المديرين وأدوارهم وصلاحياتهم
# ==============================================

"""MoulAI operational module for admin.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    String,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 🔐 ADMIN
# ==============================================


class Admin(BaseModel):
    """
    نموذج المدير - صلاحيات الإدارة والتحكم

    يدير:
        - بيانات المدير الأساسية (chat_id, username, full_name)
        - الأدوار والصلاحيات (admin, super_admin, support)
        - كلمة المرور المشفرة
        - حالة النشاط

    Attributes:
        chat_id: معرف المستخدم في تيليجرام (فريد)
        username: اسم المستخدم
        full_name: الاسم الكامل
        role: دور المدير (admin, super_admin, support)
        password_hash: كلمة المرور المشفرة
        is_active: حالة النشاط
        logs: سجل أنشطة المدير
        sessions: جلسات المدير النشطة
    """

    __tablename__ = "admins"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    chat_id = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="معرف المستخدم في تيليجرام",
    )
    username = Column(
        String(255),
        index=True,
        comment="اسم المستخدم",
    )
    full_name = Column(
        String(255),
        comment="الاسم الكامل",
    )
    role = Column(
        String(50),
        nullable=False,
        default="admin",
        comment="دور المدير: admin, super_admin, support",
    )
    password_hash = Column(
        String(255),
        comment="كلمة المرور المشفرة",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    logs = relationship(
        "AdminLog",
        back_populates="admin",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="سجل أنشطة المدير",
    )
    sessions = relationship(
        "AdminSession",
        back_populates="admin",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="جلسات المدير النشطة",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على المعرف واسم المستخدم والدور
        """
        return f"<Admin(id={self.id}, username={self.username}, role={self.role})>"
