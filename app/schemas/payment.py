# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💳 PAYMENT SCHEMAS
# نماذج Pydantic للمدفوعات
# تدير التحقق من صحة البيانات وتسلسلها للمدفوعات
# ==============================================

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# ==============================================
# 🧩 TYPES
# ==============================================

PaymentData = Dict[str, Any]
PaymentUpdateData = Dict[str, Any]
PaymentListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class PaymentBase(BaseModel):
    """
    المخطط الأساسي للدفع.
    
    يحتوي على الحقول المشتركة بين جميع مخططات الدفع.
    
    Attributes:
        owner_id: معرف المالك
        restaurant_id: معرف المطعم
        subscription_id: معرف الاشتراك (اختياري)
        payment_method: طريقة الدفع (cash, card, online)
        amount: المبلغ
        status: حالة الدفع (pending, paid, failed, cancelled)
        external_reference: المرجع الخارجي من بوابة الدفع
    """
    owner_id: int = Field(
        ...,
        description="معرف المالك",
        json_schema_extra={"example": 1},
    )
    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    subscription_id: Optional[int] = Field(
        None,
        description="معرف الاشتراك المرتبط",
        json_schema_extra={"example": 1},
    )
    payment_method: str = Field(
        ...,
        max_length=50,
        description="طريقة الدفع: cash, card, online",
        json_schema_extra={"example": "card"},
    )
    amount: float = Field(
        ...,
        gt=0,
        description="المبلغ",
        json_schema_extra={"example": 100.50},
    )
    status: str = Field(
        "pending",
        max_length=50,
        description="حالة الدفع: pending, paid, failed, cancelled",
        json_schema_extra={"example": "pending"},
    )
    external_reference: Optional[str] = Field(
        None,
        max_length=255,
        description="المرجع الخارجي من بوابة الدفع",
        json_schema_extra={"example": "pay_123456789"},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class PaymentCreate(BaseModel):
    """
    مخطط إنشاء دفع جديد.
    
    Attributes:
        owner_id: معرف المالك
        restaurant_id: معرف المطعم
        subscription_id: معرف الاشتراك (اختياري)
        payment_method: طريقة الدفع
        amount: المبلغ
        external_reference: المرجع الخارجي (اختياري)
    """
    owner_id: int = Field(
        ...,
        description="معرف المالك",
        json_schema_extra={"example": 1},
    )
    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    subscription_id: Optional[int] = Field(
        None,
        description="معرف الاشتراك المرتبط",
        json_schema_extra={"example": 1},
    )
    payment_method: str = Field(
        ...,
        max_length=50,
        description="طريقة الدفع: cash, card, online",
        json_schema_extra={"example": "card"},
    )
    amount: float = Field(
        ...,
        gt=0,
        description="المبلغ",
        json_schema_extra={"example": 100.50},
    )
    external_reference: Optional[str] = Field(
        None,
        max_length=255,
        description="المرجع الخارجي من بوابة الدفع",
        json_schema_extra={"example": "pay_123456789"},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class PaymentUpdate(BaseModel):
    """
    مخطط تحديث الدفع - جميع الحقول اختيارية.
    
    Attributes:
        status: حالة الدفع
        external_reference: المرجع الخارجي
        paid_at: تاريخ الدفع
    """
    status: Optional[str] = Field(
        None,
        max_length=50,
        description="حالة الدفع: pending, paid, failed, cancelled",
        json_schema_extra={"example": "paid"},
    )
    external_reference: Optional[str] = Field(
        None,
        max_length=255,
        description="المرجع الخارجي من بوابة الدفع",
        json_schema_extra={"example": "pay_123456789"},
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="تاريخ الدفع",
    )


# ==============================================
# 📤 STATUS UPDATE SCHEMA
# ==============================================

class PaymentStatusUpdate(BaseModel):
    """
    مخطط تحديث حالة الدفع.
    
    Attributes:
        status: الحالة الجديدة (paid, failed, cancelled)
        paid_at: تاريخ الدفع (عند التأكيد)
    """
    status: str = Field(
        ...,
        max_length=50,
        description="الحالة الجديدة: paid, failed, cancelled",
        json_schema_extra={"example": "paid"},
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="تاريخ الدفع (عند التأكيد)",
    )


# ==============================================
# 📤 CONFIRM PAYMENT SCHEMA
# ==============================================

class PaymentConfirm(BaseModel):
    """
    مخطط تأكيد الدفع.
    
    Attributes:
        external_reference: المرجع الخارجي من بوابة الدفع
        paid_at: تاريخ الدفع
    """
    external_reference: str = Field(
        ...,
        max_length=255,
        description="المرجع الخارجي من بوابة الدفع",
        json_schema_extra={"example": "pay_123456789"},
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="تاريخ الدفع (افتراضي: الآن)",
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class PaymentResponse(PaymentBase):
    """
    مخطط استجابة الدفع - يحتوي على جميع الحقول بما فيها التواريخ.
    
    Attributes:
        id: معرف الدفع
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
        paid_at: تاريخ الدفع
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الدفع",
        json_schema_extra={"example": 1},
    )
    created_at: datetime = Field(
        ...,
        description="تاريخ الإنشاء",
    )
    updated_at: datetime = Field(
        ...,
        description="تاريخ آخر تحديث",
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="تاريخ الدفع",
    )


# ==============================================
# 📋 LIST RESPONSE
# ==============================================

class PaymentListResponse(BaseModel):
    """
    مخطط استجابة قائمة المدفوعات.
    
    يحتوي على قائمة المدفوعات مع معلومات الترقيم.
    
    Attributes:
        items: قائمة المدفوعات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[PaymentResponse] = Field(
        ...,
        description="قائمة المدفوعات",
    )
    total: int = Field(
        ...,
        description="العدد الإجمالي",
        json_schema_extra={"example": 10},
        ge=0,
    )
    skip: int = Field(
        ...,
        description="عدد السجلات المتخطية",
        json_schema_extra={"example": 0},
        ge=0,
    )
    limit: int = Field(
        ...,
        description="الحد الأقصى للسجلات",
        json_schema_extra={"example": 100},
        ge=1,
    )


# ==============================================
# 📊 PAYMENT STATUS SCHEMA
# ==============================================

class PaymentStatus(BaseModel):
    """
    مخطط حالة الدفع.
    
    يحتوي على معلومات مفصلة عن حالة الدفع.
    
    Attributes:
        payment_id: معرف الدفع
        status: حالة الدفع
        is_paid: هل الدفع مدفوع؟
        is_pending: هل الدفع معلق؟
        is_failed: هل الدفع فاشل؟
        is_cancelled: هل الدفع ملغى؟
        amount: المبلغ
        paid_at: تاريخ الدفع
    """
    model_config = ConfigDict(from_attributes=True)

    payment_id: int = Field(
        ...,
        description="معرف الدفع",
        json_schema_extra={"example": 1},
    )
    status: str = Field(
        ...,
        description="حالة الدفع",
        json_schema_extra={"example": "paid"},
    )
    is_paid: bool = Field(
        ...,
        description="هل الدفع مدفوع؟",
        json_schema_extra={"example": True},
    )
    is_pending: bool = Field(
        ...,
        description="هل الدفع معلق؟",
        json_schema_extra={"example": False},
    )
    is_failed: bool = Field(
        ...,
        description="هل الدفع فاشل؟",
        json_schema_extra={"example": False},
    )
    is_cancelled: bool = Field(
        ...,
        description="هل الدفع ملغى؟",
        json_schema_extra={"example": False},
    )
    amount: float = Field(
        ...,
        description="المبلغ",
        json_schema_extra={"example": 100.50},
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="تاريخ الدفع",
    )


# ==============================================
# 📊 PAYMENT SUMMARY SCHEMA
# ==============================================

class PaymentSummary(BaseModel):
    """
    مخطط ملخص المدفوعات.
    
    يحتوي على إحصائيات موجزة عن المدفوعات.
    
    Attributes:
        total_payments: إجمالي عدد المدفوعات
        total_paid: إجمالي المدفوعات الناجحة
        total_pending: إجمالي المدفوعات المعلقة
        total_failed: إجمالي المدفوعات الفاشلة
        total_cancelled: إجمالي المدفوعات الملغاة
        total_amount: إجمالي المبلغ
        total_paid_amount: إجمالي المبلغ المدفوع
        total_pending_amount: إجمالي المبلغ المعلق
    """
    model_config = ConfigDict(from_attributes=True)

    total_payments: int = Field(
        ...,
        description="إجمالي عدد المدفوعات",
        json_schema_extra={"example": 10},
        ge=0,
    )
    total_paid: int = Field(
        ...,
        description="إجمالي المدفوعات الناجحة",
        json_schema_extra={"example": 5},
        ge=0,
    )
    total_pending: int = Field(
        ...,
        description="إجمالي المدفوعات المعلقة",
        json_schema_extra={"example": 3},
        ge=0,
    )
    total_failed: int = Field(
        ...,
        description="إجمالي المدفوعات الفاشلة",
        json_schema_extra={"example": 1},
        ge=0,
    )
    total_cancelled: int = Field(
        ...,
        description="إجمالي المدفوعات الملغاة",
        json_schema_extra={"example": 1},
        ge=0,
    )
    total_amount: float = Field(
        ...,
        description="إجمالي المبلغ",
        json_schema_extra={"example": 1000.00},
        ge=0,
    )
    total_paid_amount: float = Field(
        ...,
        description="إجمالي المبلغ المدفوع",
        json_schema_extra={"example": 500.00},
        ge=0,
    )
    total_pending_amount: float = Field(
        ...,
        description="إجمالي المبلغ المعلق",
        json_schema_extra={"example": 300.00},
        ge=0,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "PaymentBase",
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentStatusUpdate",
    "PaymentConfirm",
    "PaymentResponse",
    "PaymentListResponse",
    "PaymentStatus",
    "PaymentSummary",
    "PaymentData",
    "PaymentUpdateData",
    "PaymentListData",
]