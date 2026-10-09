# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 ADMIN SESSION MODEL
# جلسات المدير - تتبع جلسات تسجيل الدخول
# ==============================================

"""MoulAI operational module for admin session.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Boolean,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class AdminSession(BaseModel):
    """
    جلسات المدير - تتبع جلسات تسجيل الدخول.

    Attributes:
        admin_id: معرف المدير
        session_token: رمز الجلسة الفريد
        ip_address: عنوان IP للمدير
        user_agent: متصفح المدير
        expires_at: وقت انتهاء الجلسة
        is_active: حالة الجلسة
        last_activity: آخر نشاط
    """

    __tablename__ = "admin_sessions"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    admin_id = Column(
        Integer,
        ForeignKey("admins.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المدير",
    )
    session_token = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="رمز الجلسة الفريد",
    )
    ip_address = Column(
        String(45),
        nullable=True,
        comment="عنوان IP للمدير",
    )
    user_agent = Column(
        String(255),
        nullable=True,
        comment="متصفح المدير",
    )
    expires_at = Column(
        DateTime,
        nullable=False,
        comment="وقت انتهاء الجلسة",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="حالة الجلسة",
    )
    last_activity = Column(
        DateTime,
        nullable=True,
        comment="آخر نشاط",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    admin = relationship(
        "Admin",
        back_populates="sessions",
        lazy="selectin",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        return f"<AdminSession(id={self.id}, admin_id={self.admin_id}, is_active={self.is_active})>"
