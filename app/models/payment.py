# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💳 PAYMENT MODEL
# نموذج المدفوعات
# يدير المدفوعات والاشتراكات والمعاملات المالية
# ==============================================

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 💳 PAYMENT
# ==============================================

class Payment(BaseModel):
    """
    نموذج المدفوعات
    
    يدير:
        - مدفوعات الاشتراكات
        - طرق الدفع (بطاقة، تحويل بنكي، يدوي)
        - حالة الدفع (معلق، مكتمل، فاشل، مسترد)
        - المراجع الخارجية
        - تاريخ الدفع
        - العلاقات مع المالك والمطعم والاشتراك
    
    Attributes:
        owner_id: معرف المالك (ForeignKey)
        user_id : معرف المستخدم (ForeignKey)
        restaurant_id: معرف المطعم (ForeignKey)
        subscription_id: معرف الاشتراك (ForeignKey)
        payment_method: طريقة الدفع (card, bank_transfer, manual)
        amount: المبلغ
        status: حالة الدفع (pending, completed, failed, refunded)
        external_reference: المرجع الخارجي
        paid_at: تاريخ ووقت الدفع
        owner: علاقة مع نموذج Owner
        user: علاقة مع نموذج User
        restaurant: علاقة مع نموذج Restaurant (بدون back_populates)
        subscription: علاقة مع نموذج Subscription
    """
    __tablename__ = "payments"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    owner_id = Column(
        Integer,
        ForeignKey("owners.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المالك",
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="معرف المستخدم",
    )
    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المطعم",
    )
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        comment="معرف الاشتراك",
    )
    payment_method = Column(
        String(50),
        nullable=False,
        comment="طريقة الدفع: card, bank_transfer, manual",
    )
    amount = Column(
        Float,
        nullable=False,
        comment="المبلغ",
    )
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="حالة الدفع: pending, completed, failed, refunded",
    )
    external_reference = Column(
        Text,
        comment="المرجع الخارجي",
    )
    paid_at = Column(
        DateTime,
        comment="تاريخ ووقت الدفع",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    owner = relationship(
        "Owner",
        back_populates="payments",
        lazy="selectin",
        # comment="المالك",
    )
    user = relationship(
        "User",
        back_populates="payments",
        lazy="selectin",
        # comment="المستخدم",
    )
    restaurant = relationship(
        "Restaurant",
        lazy="selectin",
        # ملاحظة: لا يوجد back_populates لأن Restaurant لا يحتاج الوصول للمدفوعات
        # comment="المطعم المرتبط",
    )
    subscription = relationship(
        "Subscription",
        back_populates="payments",
        lazy="selectin",
        # comment="الاشتراك",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والمبلغ والحالة
        """
        return (
            f"<Payment(id={self.id}, amount={self.amount}, "
            f"status={self.status})>"
        )