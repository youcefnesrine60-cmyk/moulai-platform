# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📋 ORDER ITEMS MODEL
# نماذج عناصر الطلب والمدفوعات وحالة الطلب
# تدير تفاصيل الطلبات من عناصر وخيارات ومدفوعات وحالة
# ==============================================

from sqlalchemy import (
    BigInteger,
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
# 🛒 ORDER ITEM
# عنصر الطلب
# ==============================================

class OrderItem(BaseModel):
    """
    نموذج عنصر الطلب
    
    يمثل منتجاً محدداً ضمن طلب معين مع الكمية والسعر.
    
    Attributes:
        order_id: معرف الطلب (ForeignKey)
        product_id: معرف المنتج (ForeignKey)
        product_name: اسم المنتج (نسخة لحظة الطلب)
        unit_price: سعر الوحدة (نسخة لحظة الطلب)
        quantity: الكمية
        total_price: السعر الإجمالي (unit_price * quantity)
        order: علاقة مع نموذج Order
        product: علاقة مع نموذج Product
        options: قائمة خيارات العنصر
    """
    __tablename__ = "order_items"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    order_id = Column(
        BigInteger,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الطلب",
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        comment="معرف المنتج",
    )
    product_name = Column(
        String(255),
        nullable=False,
        comment="اسم المنتج (نسخة لحظة الطلب)",
    )
    unit_price = Column(
        Float,
        nullable=False,
        comment="سعر الوحدة (نسخة لحظة الطلب)",
    )
    quantity = Column(
        Integer,
        nullable=False,
        comment="الكمية",
    )
    total_price = Column(
        Float,
        nullable=False,
        comment="السعر الإجمالي (unit_price * quantity)",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    order = relationship(
        "Order",
        back_populates="items",
        lazy="selectin",
        # comment="الطلب المرتبط",
    )
    product = relationship(
        "Product",
        back_populates="order_items",
        lazy="selectin",
        # comment="المنتج المرتبط",
    )
    options = relationship(
        "OrderItemOption",
        back_populates="order_item",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="خيارات العنصر",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف واسم المنتج والكمية
        """
        return (
            f"<OrderItem(id={self.id}, product={self.product_name}, "
            f"quantity={self.quantity})>"
        )


# ==============================================
# 🎯 ORDER ITEM OPTION
# خيار عنصر الطلب
# ==============================================

class OrderItemOption(BaseModel):
    """
    نموذج خيار عنصر الطلب
    
    يمثل خياراً محدداً (مثل: إضافة جبن، حجم كبير) تم اختياره لعنصر طلب.
    
    Attributes:
        order_item_id: معرف عنصر الطلب (ForeignKey)
        option_group_name: اسم مجموعة الخيار (نسخة لحظة الطلب)
        option_name: اسم الخيار (نسخة لحظة الطلب)
        additional_price: السعر الإضافي لهذا الخيار
        order_item: علاقة مع نموذج OrderItem
    """
    __tablename__ = "order_item_options"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    order_item_id = Column(
        BigInteger,
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف عنصر الطلب",
    )
    option_group_name = Column(
        String(255),
        nullable=False,
        comment="اسم مجموعة الخيار (نسخة لحظة الطلب)",
    )
    option_name = Column(
        String(255),
        nullable=False,
        comment="اسم الخيار (نسخة لحظة الطلب)",
    )
    additional_price = Column(
        Float,
        nullable=False,
        default=0,
        comment="السعر الإضافي لهذا الخيار",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    order_item = relationship(
        "OrderItem",
        back_populates="options",
        lazy="selectin",
        # comment="عنصر الطلب المرتبط",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف واسم الخيار والسعر الإضافي
        """
        return (
            f"<OrderItemOption(id={self.id}, option={self.option_name}, "
            f"price={self.additional_price})>"
        )


# ==============================================
# 💳 ORDER PAYMENT
# دفع الطلب
# ==============================================

class OrderPayment(BaseModel):
    """
    نموذج دفع الطلب
    
    يمثل عملية دفع مرتبطة بطلب معين.
    
    Attributes:
        order_id: معرف الطلب (ForeignKey)
        payment_method: طريقة الدفع (cash, card, online)
        payment_status: حالة الدفع (pending, paid, failed, refunded)
        amount: المبلغ المدفوع
        transaction_reference: مرجع المعاملة من بوابة الدفع
        paid_at: تاريخ ووقت الدفع
        order: علاقة مع نموذج Order
    """
    __tablename__ = "order_payments"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    order_id = Column(
        BigInteger,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الطلب",
    )
    payment_method = Column(
        String(50),
        nullable=False,
        comment="طريقة الدفع: cash, card, online",
    )
    payment_status = Column(
        String(50),
        nullable=False,
        comment="حالة الدفع: pending, paid, failed, refunded",
    )
    amount = Column(
        Float,
        nullable=False,
        comment="المبلغ المدفوع",
    )
    transaction_reference = Column(
        String(255),
        nullable=True,
        comment="مرجع المعاملة من بوابة الدفع",
    )
    paid_at = Column(
        DateTime,
        nullable=True,
        comment="تاريخ ووقت الدفع",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    order = relationship(
        "Order",
        back_populates="payments",
        lazy="selectin",
        # comment="الطلب المرتبط",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف وطريقة الدفع والحالة
        """
        return (
            f"<OrderPayment(id={self.id}, method={self.payment_method}, "
            f"status={self.payment_status})>"
        )


# ==============================================
# 📊 ORDER STATUS HISTORY
# سجل حالة الطلب
# ==============================================

class OrderStatusHistory(BaseModel):
    """
    نموذج سجل حالة الطلب
    
    يتتبع جميع تغييرات حالة الطلب مع مرور الوقت.
    
    Attributes:
        order_id: معرف الطلب (ForeignKey)
        old_status: الحالة السابقة
        new_status: الحالة الجديدة
        changed_by_employee_id: معرف الموظف الذي غيّر الحالة
        note: ملاحظة إضافية عن التغيير
        order: علاقة مع نموذج Order
    """
    __tablename__ = "order_status_history"
    
    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================
    
    order_id = Column(
        BigInteger,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف الطلب",
    )
    old_status = Column(
        String(50),
        nullable=True,
        comment="الحالة السابقة",
    )
    new_status = Column(
        String(50),
        nullable=False,
        comment="الحالة الجديدة",
    )
    changed_by_employee_id = Column(
        Integer,
        nullable=True,
        comment="معرف الموظف الذي غيّر الحالة",
    )
    note = Column(
        Text,
        nullable=True,
        comment="ملاحظة إضافية عن التغيير",
    )
    
    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================
    
    order = relationship(
        "Order",
        back_populates="status_history",
        lazy="selectin",
        # comment="الطلب المرتبط",
    )
    
    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================
    
    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج
        
        Returns:
            سلسلة نصية تحتوي على المعرف والحالة السابقة والحالة الجديدة
        """
        return (
            f"<OrderStatusHistory(id={self.id}, old={self.old_status}, "
            f"new={self.new_status})>"
        )