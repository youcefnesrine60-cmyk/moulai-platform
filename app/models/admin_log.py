# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📋 ADMIN LOG MODEL
# سجل أنشطة المدير
# ==============================================

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 📋 ADMIN LOG
# ==============================================

class AdminLog(BaseModel):
    """
    سجل أنشطة المدير - تتبع جميع إجراءات المدير.
    
    Attributes:
        admin_id: معرف المدير
        action: نوع الإجراء (login, logout, create, update, delete, etc.)
        resource: نوع المورد (restaurant, order, user, etc.)
        resource_id: معرف المورد
        details: تفاصيل إضافية عن الإجراء
        ip_address: عنوان IP للمدير
        user_agent: متصفح المدير
        timestamp: وقت الإجراء
    """
    
    __tablename__ = "admin_logs"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    admin_id = Column(
        Integer,
        ForeignKey("admins.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المدير",
    )
    action = Column(
        String(50),
        nullable=False,
        comment="نوع الإجراء: login, logout, create, update, delete, view",
    )
    resource = Column(
        String(50),
        nullable=True,
        comment="نوع المورد: restaurant, order, user, product, etc.",
    )
    resource_id = Column(
        Integer,
        nullable=True,
        comment="معرف المورد",
    )
    details = Column(
        Text,
        nullable=True,
        comment="تفاصيل إضافية عن الإجراء",
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
    timestamp = Column(
        DateTime,
        nullable=False,
        comment="وقت الإجراء",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    # العلاقة مع نموذج المدير
    admin = relationship(
        "Admin",
        back_populates="logs",
        lazy="selectin",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        return f"<AdminLog(id={self.id}, admin_id={self.admin_id}, action={self.action})>"