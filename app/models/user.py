# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👤 USER MODEL
# نموذج المستخدم الأساسي
# يدير بيانات المستخدمين وموافقاتهم
# ==============================================

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    String,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


# ==============================================
# 👤 USER
# ==============================================

class User(BaseModel):
    """
    نموذج المستخدم الأساسي
    
    يدير:
        - معرف المستخدم في تيليجرام (chat_id)
        - موافقة المستخدم على الشروط والأحكام
        - العلاقات مع الطلبات والمدفوعات
    
    Attributes:
        chat_id: معرف المستخدم في تيليجرام (فريد)
        customer_name: اسم المستخدم
        customer_phone: رقم هاتف المستخدم
        consent: موافقة المستخدم على الشروط والأحكام
        orders: قائمة الطلبات التابعة للمستخدم
        payments: قائمة المدفوعات التابعة للمستخدم
    """
    __tablename__ = "users"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    chat_id = Column(
        BigInteger,
        unique=True,
        index=True,
        nullable=True,
        comment="معرف المستخدم في تيليجرام",
    )
    customer_name = Column(
        String(255), 
        nullable=True,
        comment="اسم العميل",
    )   
    customer_phone = Column(
        String(20), 
        nullable=True,
        comment="رقم هاتف العميل"
    )
    consent = Column(
        Boolean,
        default=False,
        comment="موافقة المستخدم على الشروط والأحكام",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    # قائمة الطلبات التابعة للمستخدم
    orders = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        
    )
    # قائمة المدفوعات التابعة للمستخدم
    payments = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف ومعرف المستخدم
        """
        return f"<User(id={self.id}, chat_id={self.chat_id})>"
