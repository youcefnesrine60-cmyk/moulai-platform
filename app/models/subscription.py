# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 SUBSCRIPTION MODEL
# نظام الاشتراكات والخطط والميزات
# يدير خطط الاشتراك والميزات والاشتراكات النشطة
# ==============================================

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 📋 SUBSCRIPTION PLAN
# خطة الاشتراك
# ==============================================

class SubscriptionPlan(BaseModel):
    """
    نموذج خطة الاشتراك
    
    يدير:
        - بيانات الخطة (الكود، الاسم، الوصف)
        - السعر الأساسي ونسبة الخصم
        - ترتيب العرض وحالة النشاط
        - العلاقات مع الاشتراكات والميزات
    
    Attributes:
        code: كود الخطة (فريد)
        name: اسم الخطة
        description: وصف الخطة
        base_price: السعر الأساسي
        plan_discount_percent: نسبة الخصم
        display_order: ترتيب العرض
        active: حالة النشاط
        subscriptions: قائمة الاشتراكات
        features: قائمة ميزات الخطة
        usage_limits: قائمة حدود الاستخدام
    """
    __tablename__ = "subscription_plans"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        comment="كود الخطة (فريد)",
    )
    name = Column(
        String(100),
        nullable=False,
        comment="اسم الخطة",
    )
    description = Column(
        Text,
        comment="وصف الخطة",
    )
    base_price = Column(
        Float,
        nullable=False,
        default=0,
        comment="السعر الأساسي",
    )
    plan_discount_percent = Column(
        Float,
        nullable=False,
        default=0,
        comment="نسبة الخصم",
    )
    display_order = Column(
        Integer,
        default=0,
        comment="ترتيب العرض",
    )
    active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    subscriptions = relationship(
        "Subscription",
        back_populates="plan",
        lazy="selectin",
        # comment="قائمة الاشتراكات",
    )
    features = relationship(
        "PlanFeature",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة ميزات الخطة",
    )
    usage_limits = relationship(
        "FeatureUsageLimit",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة حدود الاستخدام",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والكود والاسم
        """
        return f"<SubscriptionPlan(id={self.id}, code={self.code}, name={self.name})>"


# ==============================================
# ⚙️ FEATURE
# الميزة
# ==============================================

class Feature(BaseModel):
    """
    نموذج الميزة
    
    يدير:
        - بيانات الميزة (الكود، الاسم، الوصف)
        - العلاقات مع الخطط والاشتراكات
    
    Attributes:
        code: كود الميزة (فريد)
        name: اسم الميزة
        description: وصف الميزة
        plan_features: قائمة ميزات الخطط
        subscription_features: قائمة ميزات الاشتراكات
        feature_requests: قائمة طلبات الميزات
        pricing: قائمة تسعير الميزات
        usage_limits: قائمة حدود الاستخدام
        usage_counters: قائمة عدادات الاستخدام
    """
    __tablename__ = "features"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        comment="كود الميزة (فريد)",
    )
    name = Column(
        String(100),
        nullable=False,
        comment="اسم الميزة",
    )
    description = Column(
        Text,
        comment="وصف الميزة",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    plan_features = relationship(
        "PlanFeature",
        back_populates="feature",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة ميزات الخطط",
    )
    subscription_features = relationship(
        "SubscriptionFeature",
        back_populates="feature",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة ميزات الاشتراكات",
    )
    feature_requests = relationship(
        "SubscriptionFeatureRequest",
        back_populates="feature",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة طلبات الميزات",
    )
    pricing = relationship(
        "FeaturePricing",
        back_populates="feature",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة تسعير الميزات",
    )
    usage_limits = relationship(
        "FeatureUsageLimit",
        back_populates="feature",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة حدود الاستخدام",
    )
    usage_counters = relationship(
        "FeatureUsageCounter",
        back_populates="feature",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة عدادات الاستخدام",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والكود والاسم
        """
        return f"<Feature(id={self.id}, code={self.code}, name={self.name})>"


# ==============================================
# 📋 PLAN FEATURE
# ميزة الخطة
# ==============================================

class PlanFeature(BaseModel):
    """
    نموذج ميزة الخطة
    
    يربط الميزات بالخطط ويحدد ما إذا كانت مدرجة في الخطة.
    
    Attributes:
        plan_id: معرف الخطة (ForeignKey)
        feature_id: معرف الميزة (ForeignKey)
        included: هل الميزة مدرجة في الخطة
        plan: علاقة مع نموذج SubscriptionPlan
        feature: علاقة مع نموذج Feature
    """
    __tablename__ = "plan_features"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    plan_id = Column(
        Integer,
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الخطة",
    )
    feature_id = Column(
        Integer,
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الميزة",
    )
    included = Column(
        Boolean,
        default=True,
        comment="هل الميزة مدرجة في الخطة",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    plan = relationship(
        "SubscriptionPlan",
        back_populates="features",
        lazy="selectin",
        # comment="الخطة",
    )
    feature = relationship(
        "Feature",
        back_populates="plan_features",
        lazy="selectin",
        # comment="الميزة",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على معرف الخطة ومعرف الميزة وحالة التضمين
        """
        return (
            f"<PlanFeature(plan_id={self.plan_id}, "
            f"feature_id={self.feature_id}, included={self.included})>"
        )


# ==============================================
# 📦 SUBSCRIPTION
# الاشتراك
# ==============================================

class Subscription(BaseModel):
    """
    نموذج الاشتراك
    
    يدير:
        - اشتراكات المالكين والمطاعم
        - دورة الفوترة والمبلغ
        - تواريخ البدء والانتهاء
        - حالة الاشتراك
        - العلاقات مع المالك والمطعم والخطة
    
    Attributes:
        owner_id: معرف المالك (ForeignKey)
        restaurant_id: معرف المطعم (ForeignKey)
        plan_id: معرف الخطة (ForeignKey)
        billing_cycle: دورة الفوترة (monthly, quarterly, yearly)
        amount: المبلغ
        starts_at: تاريخ البدء
        expires_at: تاريخ الانتهاء
        status: حالة الاشتراك (pending, trial, active, expired, cancelled)
        owner: علاقة مع نموذج Owner
        restaurant: علاقة مع نموذج Restaurant
        plan: علاقة مع نموذج SubscriptionPlan
        features: قائمة ميزات الاشتراك
        feature_requests: قائمة طلبات الميزات
        payments: قائمة المدفوعات
    """
    __tablename__ = "subscriptions"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    owner_id = Column(
        Integer,
        ForeignKey("owners.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المالك",
    )
    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المطعم",
    )
    plan_id = Column(
        Integer,
        ForeignKey("subscription_plans.id"),
        nullable=False,
        comment="معرف الخطة",
    )
    billing_cycle = Column(
        String(50),
        nullable=False,
        comment="دورة الفوترة: monthly, quarterly, yearly",
    )
    amount = Column(
        Float,
        nullable=False,
        comment="المبلغ",
    )
    starts_at = Column(
        DateTime,
        comment="تاريخ البدء",
    )
    expires_at = Column(
        DateTime,
        comment="تاريخ الانتهاء",
    )
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="حالة الاشتراك: pending, trial, active, expired, cancelled",
    )
    
    # ==========================================
    # 🔒 CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        Index(
            'uq_active_subscription',
            'restaurant_id',
            unique=True,
            postgresql_where="status IN ('trial', 'active')",
            #comment="تأكد من وجود اشتراك نشط واحد فقط لكل مطعم",
        ),
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    owner = relationship(
        "Owner",
        back_populates="subscriptions",
        lazy="selectin",
        # comment="المالك",
    )
    restaurant = relationship(
        "Restaurant",
        back_populates="subscriptions",
        lazy="selectin",
        # comment="المطعم",
    )
    plan = relationship(
        "SubscriptionPlan",
        back_populates="subscriptions",
        lazy="selectin",
        # comment="الخطة",
    )
    features = relationship(
        "SubscriptionFeature",
        back_populates="subscription",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة ميزات الاشتراك",
    )
    feature_requests = relationship(
        "SubscriptionFeatureRequest",
        back_populates="subscription",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة طلبات الميزات",
    )
    payments = relationship(
        "Payment",
        back_populates="subscription",
        lazy="selectin",
        # comment="قائمة المدفوعات",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والحالة ومعرف المطعم
        """
        return (
            f"<Subscription(id={self.id}, status={self.status}, "
            f"restaurant_id={self.restaurant_id})>"
        )


# ==============================================
# 📋 SUBSCRIPTION FEATURE
# ميزة الاشتراك
# ==============================================

class SubscriptionFeature(BaseModel):
    """
    نموذج ميزة الاشتراك
    
    يربط الميزات بالاشتراكات الفعلية.
    
    Attributes:
        subscription_id: معرف الاشتراك (ForeignKey)
        feature_id: معرف الميزة (ForeignKey)
        subscription: علاقة مع نموذج Subscription
        feature: علاقة مع نموذج Feature
    """
    __tablename__ = "subscription_features"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الاشتراك",
    )
    feature_id = Column(
        Integer,
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الميزة",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    subscription = relationship(
        "Subscription",
        back_populates="features",
        lazy="selectin",
        # comment="الاشتراك",
    )
    feature = relationship(
        "Feature",
        back_populates="subscription_features",
        lazy="selectin",
        # comment="الميزة",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على معرف الاشتراك ومعرف الميزة
        """
        return (
            f"<SubscriptionFeature(subscription_id={self.subscription_id}, "
            f"feature_id={self.feature_id})>"
        )


# ==============================================
# 📋 SUBSCRIPTION FEATURE REQUEST
# طلب ميزة الاشتراك
# ==============================================

class SubscriptionFeatureRequest(BaseModel):
    """
    نموذج طلب ميزة الاشتراك
    
    يتتبع طلبات الميزات الإضافية من قبل المشتركين.
    
    Attributes:
        subscription_id: معرف الاشتراك (ForeignKey)
        feature_id: معرف الميزة (ForeignKey)
        subscription: علاقة مع نموذج Subscription
        feature: علاقة مع نموذج Feature
    """
    __tablename__ = "subscription_feature_requests"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الاشتراك",
    )
    feature_id = Column(
        Integer,
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الميزة",
    )
    
    # ==========================================
    # 🔒 CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        Index(
            'idx_subscription_feature_requests_subscription',
            'subscription_id',
            #comment="مؤشر لتحسين أداء البحث عن طلبات اشتراك معين",
        ),
        Index(
            'idx_subscription_feature_requests_feature',
            'feature_id',
            #comment="مؤشر لتحسين أداء البحث عن طلبات ميزة معينة",
        ),
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    subscription = relationship(
        "Subscription",
        back_populates="feature_requests",
        lazy="selectin",
        # comment="الاشتراك",
    )
    feature = relationship(
        "Feature",
        back_populates="feature_requests",
        lazy="selectin",
        # comment="الميزة",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على معرف الاشتراك ومعرف الميزة
        """
        return (
            f"<SubscriptionFeatureRequest(subscription_id={self.subscription_id}, "
            f"feature_id={self.feature_id})>"
        )