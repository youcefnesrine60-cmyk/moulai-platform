# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTING SCHEMAS
# نماذج Pydantic لإعدادات الدفع للمطعم
# تدير التحقق من صحة البيانات وتسلسلها لإعدادات الدفع
# ==============================================

"""MoulAI operational module for restaurant payment setting.

Part of MoulAI Platform - Agent-as-a-Service.
"""

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

PaymentSettingData = Dict[str, Any]
PaymentSettingUpdateData = Dict[str, Any]
PaymentSettingListData = List[Dict[str, Any]]
AllowedMethodsList = List[str]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class RestaurantPaymentSettingBase(BaseModel):
    """
    المخطط الأساسي لإعدادات الدفع للمطعم.

    يحتوي على الحقول المشتركة بين جميع مخططات إعدادات الدفع.

    Attributes:
        restaurant_id: معرف المطعم
        allow_cash: السماح بالدفع نقداً
        allow_card: السماح بالدفع ببطاقة POS
        allow_ccp: السماح بالدفع عبر CCP
        allow_baridimob: السماح بالدفع عبر بريدي موب
        allow_stripe: السماح بالدفع عبر Stripe
        allow_paypal: السماح بالدفع عبر PayPal
    """

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    allow_cash: bool = Field(
        True,
        description="السماح بالدفع نقداً",
        json_schema_extra={"example": True},
    )
    allow_card: bool = Field(
        True,
        description="السماح بالدفع ببطاقة POS",
        json_schema_extra={"example": True},
    )
    allow_ccp: bool = Field(
        False,
        description="السماح بالدفع عبر CCP",
        json_schema_extra={"example": False},
    )
    allow_baridimob: bool = Field(
        False,
        description="السماح بالدفع عبر بريدي موب",
        json_schema_extra={"example": False},
    )
    allow_stripe: bool = Field(
        False,
        description="السماح بالدفع عبر Stripe",
        json_schema_extra={"example": False},
    )
    allow_paypal: bool = Field(
        False,
        description="السماح بالدفع عبر PayPal",
        json_schema_extra={"example": False},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class RestaurantPaymentSettingCreate(BaseModel):
    """
    مخطط إنشاء إعدادات الدفع للمطعم.

    Attributes:
        restaurant_id: معرف المطعم
        allow_cash: السماح بالدفع نقداً (اختياري)
        allow_card: السماح بالدفع ببطاقة POS (اختياري)
        allow_ccp: السماح بالدفع عبر CCP (اختياري)
        allow_baridimob: السماح بالدفع عبر بريدي موب (اختياري)
        allow_stripe: السماح بالدفع عبر Stripe (اختياري)
        allow_paypal: السماح بالدفع عبر PayPal (اختياري)
    """

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    allow_cash: bool = Field(
        True,
        description="السماح بالدفع نقداً",
        json_schema_extra={"example": True},
    )
    allow_card: bool = Field(
        True,
        description="السماح بالدفع ببطاقة POS",
        json_schema_extra={"example": True},
    )
    allow_ccp: bool = Field(
        False,
        description="السماح بالدفع عبر CCP",
        json_schema_extra={"example": False},
    )
    allow_baridimob: bool = Field(
        False,
        description="السماح بالدفع عبر بريدي موب",
        json_schema_extra={"example": False},
    )
    allow_stripe: bool = Field(
        False,
        description="السماح بالدفع عبر Stripe",
        json_schema_extra={"example": False},
    )
    allow_paypal: bool = Field(
        False,
        description="السماح بالدفع عبر PayPal",
        json_schema_extra={"example": False},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class RestaurantPaymentSettingUpdate(BaseModel):
    """
    مخطط تحديث إعدادات الدفع - جميع الحقول اختيارية.

    Attributes:
        allow_cash: السماح بالدفع نقداً
        allow_card: السماح بالدفع ببطاقة POS
        allow_ccp: السماح بالدفع عبر CCP
        allow_baridimob: السماح بالدفع عبر بريدي موب
        allow_stripe: السماح بالدفع عبر Stripe
        allow_paypal: السماح بالدفع عبر PayPal
    """

    allow_cash: Optional[bool] = Field(
        None,
        description="السماح بالدفع نقداً",
        json_schema_extra={"example": True},
    )
    allow_card: Optional[bool] = Field(
        None,
        description="السماح بالدفع ببطاقة POS",
        json_schema_extra={"example": True},
    )
    allow_ccp: Optional[bool] = Field(
        None,
        description="السماح بالدفع عبر CCP",
        json_schema_extra={"example": False},
    )
    allow_baridimob: Optional[bool] = Field(
        None,
        description="السماح بالدفع عبر بريدي موب",
        json_schema_extra={"example": False},
    )
    allow_stripe: Optional[bool] = Field(
        None,
        description="السماح بالدفع عبر Stripe",
        json_schema_extra={"example": False},
    )
    allow_paypal: Optional[bool] = Field(
        None,
        description="السماح بالدفع عبر PayPal",
        json_schema_extra={"example": False},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class RestaurantPaymentSettingResponse(RestaurantPaymentSettingBase):
    """
    مخطط استجابة إعدادات الدفع - يحتوي على جميع الحقول بما فيها التواريخ.

    Attributes:
        id: معرف الإعداد
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الإعداد",
        json_schema_extra={"example": 1},
        ge=1,
    )
    created_at: datetime = Field(
        ...,
        description="تاريخ الإنشاء",
    )
    updated_at: datetime = Field(
        ...,
        description="تاريخ آخر تحديث",
    )


# ==============================================
# 📋 LIST RESPONSE
# ==============================================


class RestaurantPaymentSettingListResponse(BaseModel):
    """
    مخطط استجابة قائمة إعدادات الدفع للمطعم.

    يحتوي على قائمة إعدادات الدفع مع معلومات الترقيم.

    Attributes:
        items: قائمة إعدادات الدفع
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[RestaurantPaymentSettingResponse] = Field(
        ...,
        description="قائمة إعدادات الدفع",
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
# 📋 PAYMENT METHODS LIST
# ==============================================


class PaymentMethodsList(BaseModel):
    """
    مخطط قائمة طرق الدفع المسموح بها.

    Attributes:
        restaurant_id: معرف المطعم
        allowed_methods: قائمة طرق الدفع المسموح بها
        all_methods: قائمة جميع طرق الدفع المتاحة
    """

    model_config = ConfigDict(from_attributes=True)

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    allowed_methods: AllowedMethodsList = Field(
        ...,
        description="قائمة طرق الدفع المسموح بها",
        json_schema_extra={"example": ["cash", "card"]},
    )
    all_methods: AllowedMethodsList = Field(
        ...,
        description="قائمة جميع طرق الدفع المتاحة",
        json_schema_extra={
            "example": ["cash", "card", "ccp", "baridimob", "stripe", "paypal"]
        },
    )


# ==============================================
# 📊 PAYMENT SETTINGS SUMMARY
# ==============================================


class PaymentSettingsSummary(BaseModel):
    """
    مخطط ملخص إعدادات الدفع.

    Attributes:
        restaurant_id: معرف المطعم
        total_enabled: عدد طرق الدفع المفعّلة
        total_disabled: عدد طرق الدفع المعطّلة
        enabled_methods: قائمة طرق الدفع المفعّلة
        disabled_methods: قائمة طرق الدفع المعطّلة
    """

    model_config = ConfigDict(from_attributes=True)

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
    )
    total_enabled: int = Field(
        ...,
        description="عدد طرق الدفع المفعّلة",
        json_schema_extra={"example": 2},
        ge=0,
    )
    total_disabled: int = Field(
        ...,
        description="عدد طرق الدفع المعطّلة",
        json_schema_extra={"example": 4},
        ge=0,
    )
    enabled_methods: AllowedMethodsList = Field(
        ...,
        description="قائمة طرق الدفع المفعّلة",
        json_schema_extra={"example": ["cash", "card"]},
    )
    disabled_methods: AllowedMethodsList = Field(
        ...,
        description="قائمة طرق الدفع المعطّلة",
        json_schema_extra={"example": ["ccp", "baridimob", "stripe", "paypal"]},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Restaurant Payment Setting
    "RestaurantPaymentSettingBase",
    "RestaurantPaymentSettingCreate",
    "RestaurantPaymentSettingUpdate",
    "RestaurantPaymentSettingResponse",
    "RestaurantPaymentSettingListResponse",
    # Payment Methods List
    "PaymentMethodsList",
    # Payment Settings Summary
    "PaymentSettingsSummary",
    # Types
    "PaymentSettingData",
    "PaymentSettingUpdateData",
    "PaymentSettingListData",
]
