# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💰 FEATURE PRICING & USAGE MODELS
# نماذج تسعير الميزات والاستخدام
# تدير تسعير الميزات وحدود الاستخدام وعدادات الاستخدام
# ==============================================

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 💲 FEATURE PRICING
# تسعير الميزة
# ==============================================

class FeaturePricing(BaseModel):
    """
    نموذج تسعير الميزة
    
    يدير:
        - تسعير الميزات حسب دورة الفوترة
        - السعر لكل ميزة
        - حالة النشاط
        - العلاقة مع الميزة
    
    Attributes:
        feature_id: معرف الميزة (ForeignKey)
        billing_cycle: دورة الفوترة (monthly, yearly)
        price: السعر
        active: حالة النشاط
        feature: علاقة مع نموذج Feature
    """
    __tablename__ = "feature_pricing"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    feature_id = Column(
        Integer,
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الميزة",
    )
    billing_cycle = Column(
        String(50),
        nullable=False,
        comment="دورة الفوترة: monthly, yearly",
    )
    price = Column(
        Float,
        nullable=False,
        comment="السعر",
    )
    active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    feature = relationship(
        "Feature",
        back_populates="pricing",
        lazy="selectin",
        # comment="الميزة المرتبطة",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على معرف الميزة والسعر
        """
        return (
            f"<FeaturePricing(feature_id={self.feature_id}, "
            f"price={self.price})>"
        )


# ==============================================
# 📊 FEATURE USAGE LIMIT
# حد استخدام الميزة
# ==============================================

class FeatureUsageLimit(BaseModel):
    """
    نموذج حد استخدام الميزة
    
    يدير:
        - حدود استخدام الميزات حسب الخطة
        - نوع الحد (hard, soft)
        - العلاقات مع الخطة والميزة
    
    Attributes:
        plan_id: معرف الخطة (ForeignKey)
        feature_id: معرف الميزة (ForeignKey)
        monthly_limit: الحد الشهري
        limit_type: نوع الحد (hard, soft)
        plan: علاقة مع نموذج SubscriptionPlan
        feature: علاقة مع نموذج Feature
    """
    __tablename__ = "feature_usage_limits"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    plan_id = Column(
        Integer,
        ForeignKey("subscription_plans.id"),
        nullable=False,
        comment="معرف الخطة",
    )
    feature_id = Column(
        Integer,
        ForeignKey("features.id"),
        nullable=False,
        comment="معرف الميزة",
    )
    monthly_limit = Column(
        Integer,
        comment="الحد الشهري",
    )
    limit_type = Column(
        String(50),
        comment="نوع الحد: hard, soft",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    plan = relationship(
        "SubscriptionPlan",
        back_populates="usage_limits",
        lazy="selectin",
        # comment="الخطة المرتبطة",
    )
    feature = relationship(
        "Feature",
        back_populates="usage_limits",
        lazy="selectin",
        # comment="الميزة المرتبطة",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على معرف الخطة ومعرف الميزة والحد
        """
        return (
            f"<FeatureUsageLimit(plan_id={self.plan_id}, "
            f"feature_id={self.feature_id}, limit={self.monthly_limit})>"
        )


# ==============================================
# 🔢 FEATURE USAGE COUNTER
# عداد استخدام الميزة
# ==============================================

class FeatureUsageCounter(BaseModel):
    """
    نموذج عداد استخدام الميزة
    
    يدير:
        - تتبع استخدام الميزات لكل مطعم
        - العد الشهري والسنوي
        - العلاقات مع المطعم والميزة
    
    Attributes:
        restaurant_id: معرف المطعم (ForeignKey)
        feature_id: معرف الميزة (ForeignKey)
        usage_count: عدد مرات الاستخدام
        period_year: السنة
        period_month: الشهر
        restaurant: علاقة مع نموذج Restaurant
        feature: علاقة مع نموذج Feature
    """
    __tablename__ = "feature_usage_counters"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المطعم",
    )
    feature_id = Column(
        Integer,
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الميزة",
    )
    usage_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="عدد مرات الاستخدام",
    )
    period_year = Column(
        Integer,
        comment="السنة",
    )
    period_month = Column(
        Integer,
        comment="الشهر",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    restaurant = relationship(
        "Restaurant",
        back_populates="feature_usage_counters",
        lazy="selectin",
        # comment="المطعم المرتبط",
    )
    feature = relationship(
        "Feature",
        back_populates="usage_counters",
        lazy="selectin",
        # comment="الميزة المرتبطة",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على معرف المطعم ومعرف الميزة والاستخدام
        """
        return (
            f"<FeatureUsageCounter(restaurant_id={self.restaurant_id}, "
            f"feature_id={self.feature_id}, usage={self.usage_count})>"
        )


# ==============================================
# 🏢 BRANCH PRICING
# تسعير الفروع
# ==============================================

class BranchPricing(BaseModel):
    """
    نموذج تسعير الفروع
    
    يدير:
        - تسعير الفروع حسب عدد الفروع
        - حدود عدد الفروع (الحد الأدنى والأقصى)
        - السعر لكل فرع
        - حالة النشاط
    
    Attributes:
        min_branches: الحد الأدنى لعدد الفروع
        max_branches: الحد الأقصى لعدد الفروع
        price_per_branch: السعر لكل فرع
        active: حالة النشاط
    """
    __tablename__ = "branch_pricing"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    min_branches = Column(
        Integer,
        nullable=False,
        comment="الحد الأدنى لعدد الفروع",
    )
    max_branches = Column(
        Integer,
        comment="الحد الأقصى لعدد الفروع",
    )
    price_per_branch = Column(
        Float,
        nullable=False,
        comment="السعر لكل فرع",
    )
    active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على الحد الأدنى والحد الأقصى والسعر
        """
        return (
            f"<BranchPricing(min={self.min_branches}, "
            f"max={self.max_branches}, price={self.price_per_branch})>"
        )