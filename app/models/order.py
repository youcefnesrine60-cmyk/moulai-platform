# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📋 ORDER MODEL
# نموذج الطلب
# يدير الطلبات بكامل تفاصيلها من البداية إلى النهاية
# ==============================================

from sqlalchemy import (
    Column,
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
# 📋 ORDER
# ==============================================

class Order(BaseModel):
    """
    نموذج الطلب
    
    يدير:
        - بيانات الطلب الأساسية (الرقم، النوع، الحالة)
        - معلومات العميل (الاسم، الهاتف، العنوان)
        - المبالغ (الإجمالي، الخصم، الضريبة، التوصيل)
        - الملاحظات
        - العلاقات مع المطعم والفرع والموظف
    
    Attributes:
        restaurant_id: معرف المطعم (ForeignKey)
        branch_id: معرف الفرع (ForeignKey)
        table_id: معرف الطاولة
        employee_id: معرف الموظف
        order_number: رقم الطلب (فريد لكل مطعم)
        order_type: نوع الطلب (dine_in, takeaway, delivery)
        delivery_address: عنوان التوصيل
        customer_note: ملاحظات العميل
        status: حالة الطلب (pending, confirmed, preparing, ready, completed, cancelled)
        subtotal_amount: المبلغ الإجمالي قبل الخصم
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المبلغ الإجمالي النهائي
        restaurant: علاقة مع نموذج Restaurant
        branch: علاقة مع نموذج Branch
        items: قائمة بنود الطلب
        payments: قائمة مدفوعات الطلب
        status_history: سجل حالات الطلب
    """
    __tablename__ = "orders"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
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
    branch_id = Column(
        Integer,
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
        comment="معرف الفرع",
    )
    table_id = Column(
        Integer,
        nullable=True,
        comment="معرف الطاولة",
    )
    employee_id = Column(
        Integer,
        nullable=True,
        comment="معرف الموظف",
    )
    order_number = Column(
        String(50),
        nullable=False,
        comment="رقم الطلب",
    )
    order_type = Column(
        String(30),
        nullable=False,
        comment="نوع الطلب: dine_in, takeaway, delivery",
    )
    delivery_address = Column(
        Text,
        comment="عنوان التوصيل",
    )
    customer_note = Column(
        Text,
        comment="ملاحظات العميل",
    )
    status = Column(
        String(50),
        nullable=False,
        comment="حالة الطلب: pending, confirmed, preparing, ready, completed, cancelled",
    )
    
    # ==========================================
    # 💰 AMOUNTS
    # ==========================================
    
    subtotal_amount = Column(
        Float,
        nullable=False,
        default=0,
        comment="المبلغ الإجمالي قبل الخصم",
    )
    discount_amount = Column(
        Float,
        nullable=False,
        default=0,
        comment="مبلغ الخصم",
    )
    tax_amount = Column(
        Float,
        nullable=False,
        default=0,
        comment="مبلغ الضريبة",
    )
    delivery_amount = Column(
        Float,
        nullable=False,
        default=0,
        comment="مبلغ التوصيل",
    )
    total_amount = Column(
        Float,
        nullable=False,
        default=0,
        comment="المبلغ الإجمالي النهائي",
    )
    
    # ==========================================
    # 🔒 CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        Index(
            'idx_orders_restaurant',
            'restaurant_id',
            #comment="مؤشر لتحسين أداء البحث عن طلبات مطعم معين",
        ),
        Index(
            'idx_orders_branch',
            'branch_id',
            #comment="مؤشر لتحسين أداء البحث عن طلبات فرع معين",
        ),
        Index(
            'idx_orders_status',
            'status',
            #comment="مؤشر لتحسين أداء البحث عن طلبات بحالة معينة",
        ),
        Index(
            'idx_orders_created_at',
            'created_at',
            #comment="مؤشر لتحسين أداء البحث عن طلبات بفترة زمنية معينة",
        ),
        Index(
            'idx_orders_restaurant_order_number',
            'restaurant_id',
            'order_number',
            unique=True,
            #comment="تأكد من عدم تكرار رقم الطلب لنفس المطعم",
        ),
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    # المستخدم
    user = relationship(
        "User", 
        back_populates="orders"
    )
    # المطعم
    restaurant = relationship(
        "Restaurant",
        back_populates="orders",
        lazy="selectin"
    )
    # الفرع
    branch = relationship(
        "Branch",
        back_populates="orders",
        lazy="selectin"
    )
    # قائمة بنود الطلب
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    # قائمة مدفوعات الطلب
    payments = relationship(
        "OrderPayment",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    # سجل حالات الطلب"
    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف ورقم الطلب والحالة
        """
        return f"<Order(id={self.id}, number={self.order_number}, status={self.status})>"