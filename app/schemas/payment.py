# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PAYMENT INPUT AND RESPONSE SCHEMAS
# Validate payment data and serialize the existing payment and statistics contracts.
# ==============================================

"""Validate payment data and serialize the existing payment and statistics contracts."""

from __future__ import annotations

# isort: split
# ==============================================
# IMPORTS
# Declare the standard-library, framework and project dependencies used below.
# ==============================================

from datetime import datetime
from decimal import Decimal
from typing import (
    Any,
    TypeAlias,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

# ==============================================
# 🧩 TYPES
# Describe shared input, update and result structures for this module.
# ==============================================

PaymentData: TypeAlias = dict[str, Any]
PaymentUpdateData: TypeAlias = dict[str, Any]
PaymentListData: TypeAlias = list[dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# المخطط الأساسي للدفع.
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

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

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
    subscription_id: int | None = Field(
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
    amount: Decimal = Field(
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
    external_reference: str | None = Field(
        None,
        max_length=255,
        description="المرجع الخارجي من بوابة الدفع",
        json_schema_extra={"example": "pay_123456789"},
    )


# ==============================================
# 📥 CREATE SCHEMA
# مخطط إنشاء دفع جديد.
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

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

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
    subscription_id: int | None = Field(
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
    amount: Decimal = Field(
        ...,
        gt=0,
        description="المبلغ",
        json_schema_extra={"example": 100.50},
    )
    external_reference: str | None = Field(
        None,
        max_length=255,
        description="المرجع الخارجي من بوابة الدفع",
        json_schema_extra={"example": "pay_123456789"},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# مخطط تحديث الدفع - جميع الحقول اختيارية.
# ==============================================


class PaymentUpdate(BaseModel):
    """
    مخطط تحديث الدفع - جميع الحقول اختيارية.

    Attributes:
        status: حالة الدفع
        external_reference: المرجع الخارجي
        paid_at: تاريخ الدفع
    """

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    status: str | None = Field(
        None,
        max_length=50,
        description="حالة الدفع: pending, paid, failed, cancelled",
        json_schema_extra={"example": "paid"},
    )
    external_reference: str | None = Field(
        None,
        max_length=255,
        description="المرجع الخارجي من بوابة الدفع",
        json_schema_extra={"example": "pay_123456789"},
    )
    paid_at: datetime | None = Field(
        None,
        description="تاريخ الدفع",
    )


# ==============================================
# 📤 STATUS UPDATE SCHEMA
# مخطط تحديث حالة الدفع.
# ==============================================


class PaymentStatusUpdate(BaseModel):
    """
    مخطط تحديث حالة الدفع.

    Attributes:
        status: الحالة الجديدة (paid, failed, cancelled)
        paid_at: تاريخ الدفع (عند التأكيد)
    """

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    status: str = Field(
        ...,
        max_length=50,
        description="الحالة الجديدة: paid, failed, cancelled",
        json_schema_extra={"example": "paid"},
    )
    paid_at: datetime | None = Field(
        None,
        description="تاريخ الدفع (عند التأكيد)",
    )


# ==============================================
# 📤 CONFIRM PAYMENT SCHEMA
# مخطط تأكيد الدفع.
# ==============================================


class PaymentConfirm(BaseModel):
    """
    مخطط تأكيد الدفع.

    Attributes:
        external_reference: المرجع الخارجي من بوابة الدفع
        paid_at: تاريخ الدفع
    """

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    external_reference: str = Field(
        ...,
        max_length=255,
        description="المرجع الخارجي من بوابة الدفع",
        json_schema_extra={"example": "pay_123456789"},
    )
    paid_at: datetime | None = Field(
        None,
        description="تاريخ الدفع (افتراضي: الآن)",
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# مخطط استجابة الدفع - يحتوي على جميع الحقول بما فيها التواريخ.
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

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    payment_provider: str | None = None
    currency: str = "DZD"

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
    paid_at: datetime | None = Field(
        None,
        description="تاريخ الدفع",
    )


# ==============================================
# 📋 LIST RESPONSE
# مخطط استجابة قائمة المدفوعات.
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

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

    model_config = ConfigDict(from_attributes=True)

    items: list[PaymentResponse] = Field(
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
# مخطط حالة الدفع.
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

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

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
    amount: Decimal = Field(
        ...,
        description="المبلغ",
        json_schema_extra={"example": 100.50},
    )
    paid_at: datetime | None = Field(
        None,
        description="تاريخ الدفع",
    )


# ==============================================
# 📊 PAYMENT SUMMARY SCHEMA
# مخطط ملخص المدفوعات.
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

    # ==============================================
    # CONTRACT FIELDS
    # Describe the fields accepted or returned by this declared data contract.
    # ==============================================

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
    total_amount: Decimal = Field(
        ...,
        description="إجمالي المبلغ",
        json_schema_extra={"example": 1000.00},
        ge=0,
    )
    total_paid_amount: Decimal = Field(
        ...,
        description="إجمالي المبلغ المدفوع",
        json_schema_extra={"example": 500.00},
        ge=0,
    )
    total_pending_amount: Decimal = Field(
        ...,
        description="إجمالي المبلغ المعلق",
        json_schema_extra={"example": 300.00},
        ge=0,
    )


# ==============================================
# 📋 EXPORTS
# Declare the public names intentionally exposed to importing modules.
# ==============================================

__all__ = [
    "PaymentBase",
    "PaymentConfirm",
    "PaymentCreate",
    "PaymentData",
    "PaymentListData",
    "PaymentListResponse",
    "PaymentResponse",
    "PaymentStatus",
    "PaymentStatusUpdate",
    "PaymentSummary",
    "PaymentUpdate",
    "PaymentUpdateData",
]
