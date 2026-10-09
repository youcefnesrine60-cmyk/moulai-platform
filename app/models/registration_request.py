# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📝 REGISTRATION REQUEST MODEL
# نموذج طلب التسجيل
# يدير طلبات تسجيل المالكين والمطاعم الجديدة
# ==============================================

"""MoulAI operational module for registration request.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 📝 REGISTRATION REQUEST
# ==============================================


class RegistrationRequest(BaseModel):
    """
    نموذج طلب التسجيل - طلب مالك جديد للتسجيل.

     يدير:
         - بيانات المالك (الاسم، الهاتف، البريد الإلكتروني)
         - بيانات المطعم (الاسم، النوع، الهاتف، الموقع)
         - حالة الطلب (pending, approved, rejected)
         - العلاقة مع المالك بعد الموافقة

     Attributes:
         chat_id: معرف المستخدم في تيليجرام
         full_name: الاسم الكامل للمالك
         owner_phone: رقم هاتف المالك
         email: البريد الإلكتروني للمالك
         restaurant_name: اسم المطعم
         restaurant_type: نوع المطعم
         restaurant_phone: رقم هاتف المطعم
         wilaya: الولاية
         lat: خط العرض (الإحداثي)
         lng: خط الطول (الإحداثي)
         status: حالة الطلب (pending, approved, rejected)
         owner_id: معرف المالك بعد الموافقة (ForeignKey)
         owner: علاقة مع نموذج Owner
    """

    __tablename__ = "registration_requests"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    chat_id = Column(
        BigInteger,
        nullable=False,
        comment="معرف المستخدم في تيليجرام",
    )
    full_name = Column(
        Text,
        nullable=False,
        comment="الاسم الكامل للمالك",
    )
    owner_phone = Column(
        Text,
        nullable=False,
        comment="رقم هاتف المالك",
    )
    email = Column(
        Text,
        comment="البريد الإلكتروني للمالك",
    )
    restaurant_name = Column(
        Text,
        nullable=False,
        comment="اسم المطعم",
    )
    restaurant_type = Column(
        Text,
        nullable=False,
        comment="نوع المطعم",
    )
    restaurant_phone = Column(
        Text,
        nullable=False,
        comment="رقم هاتف المطعم",
    )
    wilaya = Column(
        Text,
        comment="الولاية",
    )
    lat = Column(
        Float,
        comment="خط العرض (الإحداثي)",
    )
    lng = Column(
        Float,
        comment="خط الطول (الإحداثي)",
    )
    status = Column(
        Text,
        nullable=False,
        default="pending",
        comment="حالة الطلب: pending, approved, rejected",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    owner_id = Column(
        Integer,
        ForeignKey("owners.id"),
        nullable=True,
        # comment="معرف المالك المرتبط بعد الموافقة",
    )
    owner = relationship(
        "Owner",
        back_populates="registration_requests",
        lazy="selectin",
        # comment="المالك المرتبط بعد الموافقة",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على المعرف والحالة واسم المطعم
        """
        return (
            f"<RegistrationRequest(id={self.id}, status={self.status}, "
            f"restaurant={self.restaurant_name})>"
        )
