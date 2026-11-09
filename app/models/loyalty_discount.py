# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# DISCOUNT AND PROMOTION MODELS
# Map loyalty tiers, restaurant-count discounts and targeted promotional campaigns.
# ==============================================

"""Map loyalty tiers, restaurant-count discounts and targeted promotional campaigns."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 🎖️ LOYALTY DISCOUNT
# خصم الولاء
# ==============================================


class LoyaltyDiscount(BaseModel):
    """
    نموذج خصم الولاء

    يمنح خصومات للعملاء بناءً على عدد سنوات الاشتراك.

    Attributes:
        owner_id: معرف المالك (ForeignKey) - اختياري
        years_required: عدد السنوات المطلوبة للحصول على الخصم
        discount_percent: نسبة الخصم
        owner: علاقة مع نموذج Owner
    """

    # ==============================================
    # PERSISTED FIELDS AND RELATIONSHIPS
    # Declare this entity's stored fields, integrity metadata and ORM links.
    # ==============================================

    __tablename__ = "loyalty_discounts"

    # ==============================================
    # 🗂️ COLUMNS
    # Declare the mapped fields and their existing database storage requirements.
    # ==============================================

    owner_id = Column(
        Integer,
        ForeignKey("owners.id", ondelete="CASCADE"),
        nullable=True,
        comment="معرف المالك (None = عام لجميع المالكين)",
    )
    years_required = Column(
        Integer,
        nullable=False,
        comment="عدد السنوات المطلوبة للحصول على الخصم",
    )
    discount_percent = Column(
        Numeric(12, 8),
        nullable=False,
        comment="نسبة الخصم",
    )

    # ==============================================
    # 🔗 RELATIONSHIPS
    # Declare ORM links to the related persisted entities.
    # ==============================================

    owner = relationship(
        "Owner",
        back_populates="loyalty_discounts",
        lazy="selectin",
        # comment="المالك المرتبط (اختياري)",
    )

    # ==============================================
    # 📝 REPRESENTATION
    # تمثيل نصي للنموذج
    # ==============================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على عدد السنوات ونسبة الخصم
        """
        return (
            f"<LoyaltyDiscount(years={self.years_required}, "
            f"discount={self.discount_percent}%)>"
        )


# ==============================================
# 🏪 MULTI RESTAURANT DISCOUNT
# خصم المطاعم المتعددة
# ==============================================


class MultiRestaurantDiscount(BaseModel):
    """
    نموذج خصم المطاعم المتعددة

    يمنح خصومات للمالكين بناءً على عدد المطاعم المملوكة.

    Attributes:
        min_restaurants: الحد الأدنى لعدد المطاعم للحصول على الخصم
        discount_percent: نسبة الخصم
    """

    # ==============================================
    # PERSISTED FIELDS AND RELATIONSHIPS
    # Declare this entity's stored fields, integrity metadata and ORM links.
    # ==============================================

    __tablename__ = "multi_restaurant_discounts"

    # ==============================================
    # 🗂️ COLUMNS
    # Declare the mapped fields and their existing database storage requirements.
    # ==============================================

    min_restaurants = Column(
        Integer,
        nullable=False,
        comment="الحد الأدنى لعدد المطاعم للحصول على الخصم",
    )
    discount_percent = Column(
        Numeric(12, 8),
        nullable=False,
        comment="نسبة الخصم",
    )

    # ==============================================
    # 📝 REPRESENTATION
    # تمثيل نصي للنموذج
    # ==============================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على الحد الأدنى ونسبة الخصم
        """
        return (
            f"<MultiRestaurantDiscount(min={self.min_restaurants}, "
            f"discount={self.discount_percent}%)>"
        )


# ==============================================
# 🎉 PROMOTION
# عرض ترويجي
# ==============================================


class Promotion(BaseModel):
    """
    نموذج العرض الترويجي

    يدير العروض الترويجية للمطاعم مع تواريخ الصلاحية.

    Attributes:
        restaurant_id: معرف المطعم (ForeignKey) - اختياري
        name: اسم العرض الترويجي
        discount_percent: نسبة الخصم
        starts_at: تاريخ بدء العرض
        expires_at: تاريخ انتهاء العرض
        active: حالة النشاط
        restaurant: علاقة مع نموذج Restaurant
    """

    # ==============================================
    # PERSISTED FIELDS AND RELATIONSHIPS
    # Declare this entity's stored fields, integrity metadata and ORM links.
    # ==============================================

    __tablename__ = "promotions"

    # ==============================================
    # 🗂️ COLUMNS
    # Declare the mapped fields and their existing database storage requirements.
    # ==============================================

    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=True,
        comment="معرف المطعم (None = عام لجميع المطاعم)",
    )
    name = Column(
        String(255),
        nullable=False,
        comment="اسم العرض الترويجي",
    )
    discount_percent = Column(
        Numeric(12, 8),
        nullable=False,
        comment="نسبة الخصم",
    )
    starts_at = Column(
        DateTime,
        comment="تاريخ بدء العرض",
    )
    expires_at = Column(
        DateTime,
        comment="تاريخ انتهاء العرض",
    )
    active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )

    # ==============================================
    # 🔗 RELATIONSHIPS
    # Declare ORM links to the related persisted entities.
    # ==============================================

    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True)
    priority = Column(Integer, nullable=False, default=0, server_default="0")

    restaurant = relationship(
        "Restaurant",
        back_populates="promotions",
        lazy="selectin",
        # comment="المطعم المرتبط (اختياري)",
    )

    # ==============================================
    # 📝 REPRESENTATION
    # تمثيل نصي للنموذج
    # ==============================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على المعرف والاسم ونسبة الخصم
        """
        return (
            f"<Promotion(id={self.id}, name={self.name}, "
            f"discount={self.discount_percent}%)>"
        )
