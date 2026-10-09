# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👤 OWNER MODEL
# مسؤول عن نموذج مالك المطعم
# يدير بيانات المالك وصلاحياته واشتراكاته
# ==============================================

"""MoulAI operational module for owner.

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
# 👤 OWNER
# ==============================================


class Owner(BaseModel):
    """
    نموذج مالك المطعم

    يدير:
        - البيانات الشخصية للمالك
        - حالة التسجيل (pending/approved/rejected)
        - صلاحية الاستخدام التجريبي
        - العلاقات مع المطاعم والمجموعات والاشتراكات

    Attributes:
        chat_id: معرف المستخدم في تيليجرام (فريد)
        full_name: الاسم الكامل للمالك
        phone: رقم الهاتف
        email: البريد الإلكتروني
        registration_status: حالة التسجيل (pending/approved/rejected)
        trial_used: هل تم استخدام الفترة التجريبية
        restaurants: قائمة المطاعم التابعة للمالك
        restaurant_groups: قائمة مجموعات المطاعم
        subscriptions: قائمة الاشتراكات
        payments: قائمة المدفوعات
        registration_requests: قائمة طلبات التسجيل
        loyalty_discounts: قائمة خصومات الولاء
    """

    __tablename__ = "owners"

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
    auth_subject = Column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
        comment="Stable subject identifier from the trusted identity provider",
    )
    full_name = Column(
        String(255),
        comment="الاسم الكامل للمالك",
    )
    phone = Column(
        String(20),
        comment="رقم الهاتف",
    )
    email = Column(
        String(255),
        comment="البريد الإلكتروني",
    )
    registration_status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="حالة التسجيل: pending, approved, rejected",
    )
    trial_used = Column(
        Boolean,
        default=False,
        comment="هل تم استخدام الفترة التجريبية",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    restaurants = relationship(
        "Restaurant",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة المطاعم التابعة للمالك",
    )
    restaurant_groups = relationship(
        "RestaurantGroup",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة مجموعات المطاعم",
    )
    subscriptions = relationship(
        "Subscription",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة الاشتراكات",
    )
    payments = relationship(
        "Payment",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة المدفوعات",
    )
    registration_requests = relationship(
        "RegistrationRequest",
        back_populates="owner",
        lazy="selectin",
        # comment="قائمة طلبات التسجيل",
    )
    loyalty_discounts = relationship(
        "LoyaltyDiscount",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة خصومات الولاء",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على المعرف والاسم
        """
        return f"<Owner(id={self.id}, chat_id={self.chat_id}, name={self.full_name})>"
