# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏪 RESTAURANT MODEL
# نموذج المطعم الرئيسي
# يدير بيانات المطعم وموقعه وصلاحياته وعلاقاته
# ==============================================

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


# ==============================================
# 🏪 RESTAURANT
# ==============================================

class Restaurant(BaseModel):
    """
    نموذج المطعم الرئيسي
    
    يدير:
        - البيانات الأساسية للمطعم (الاسم، النوع، الهاتف)
        - الموقع الجغرافي (wilaya, lat, lng)
        - حالة النشاط (is_active)
        - العلاقات مع المالك والمجموعات والفروع
        - العلاقات مع المنتجات والطلبات والاشتراكات
    
    Attributes:
        owner_id: معرف المالك (ForeignKey)
        group_id: معرف مجموعة المطاعم (ForeignKey)
        name: اسم المطعم
        type: نوع المطعم (pizza, burger, cafe, etc.)
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض (الإحداثي)
        lng: خط الطول (الإحداثي)
        is_active: حالة النشاط
        owner: علاقة مع نموذج Owner
        group: علاقة مع نموذج RestaurantGroup
        branches: قائمة الفروع
        categories: قائمة التصنيفات
        products: قائمة المنتجات
        orders: قائمة الطلبات
        subscriptions: قائمة الاشتراكات
        metrics: مقاييس المطعم
        order_counter: عداد الطلبات
        feature_usage_counters: عدادات استخدام الميزات
        agents: وكلاء المطعم الذكية
    """
    
    __tablename__ = "restaurants"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    owner_id = Column(
        Integer,
        ForeignKey("owners.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المالك",
    )
    group_id = Column(
        Integer,
        ForeignKey("restaurant_groups.id", ondelete="SET NULL"),
        nullable=True,
        comment="معرف مجموعة المطاعم",
    )
    name = Column(
        String(255),
        nullable=False,
        comment="اسم المطعم",
    )
    type = Column(
        String(100),
        nullable=False,
        comment="نوع المطعم: pizza, burger, cafe, etc.",
    )
    phone = Column(
        String(20),
        nullable=False,
        comment="رقم الهاتف",
    )
    wilaya = Column(
        String(100),
        nullable=False,
        comment="الولاية",
    )
    lat = Column(
        Float,
        nullable=True,
        comment="خط العرض (الإحداثي)",
    )
    lng = Column(
        Float,
        nullable=True,
        comment="خط الطول (الإحداثي)",
    )
    is_active = Column(
        Boolean,
        default=True,
        comment="حالة النشاط",
    )
    
    # ==========================================
    # 🔒 CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        UniqueConstraint(
            'owner_id',
            'name',
            'phone',
            'wilaya',
            'lat',
            'lng',
            name='uq_restaurant_location',
        ),
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    # 👤 المالك
    owner = relationship(
        "Owner",
        back_populates="restaurants",
        lazy="selectin",
    )
    
    # 🏢 مجموعة المطاعم
    group = relationship(
        "RestaurantGroup",
        back_populates="restaurants",
        lazy="selectin",
    )
    
    # 📍 الفروع
    branches = relationship(
        "Branch",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # 📂 التصنيفات
    categories = relationship(
        "Category",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # 🍽️ المنتجات
    products = relationship(
        "Product",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # 📋 الطلبات
    orders = relationship(
        "Order",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # 💳 الاشتراكات
    subscriptions = relationship(
        "Subscription",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # 📊 مقاييس المطعم
    metrics = relationship(
        "RestaurantMetric",
        back_populates="restaurant",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # 🔢 عداد الطلبات
    order_counter = relationship(
        "RestaurantOrderCounter",
        back_populates="restaurant",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # 📈 عدادات استخدام الميزات
    feature_usage_counters = relationship(
        "FeatureUsageCounter",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ✅ إعدادات الدفع
    payment_settings = relationship(
        "RestaurantPaymentSetting",
        back_populates="restaurant",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # 🤖 وكلاء المطعم الذكية
    agents = relationship(
        "Agent",
        back_populates="restaurant",
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
            سلسلة نصية تحتوي على المعرف والاسم والنوع
        """
        return f"<Restaurant(id={self.id}, name={self.name}, type={self.type})>"