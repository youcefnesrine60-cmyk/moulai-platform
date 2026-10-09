# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📋 REGISTRATION REQUEST SCHEMAS
# نماذج Pydantic لطلبات التسجيل
# ==============================================

"""MoulAI operational module for registration request.

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
    field_validator,
)

# ==============================================
# 🧩 TYPES
# ==============================================

RegistrationRequestData = Dict[str, Any]
RegistrationRequestUpdateData = Dict[str, Any]
RegistrationRequestListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class RegistrationRequestBase(BaseModel):
    """
    النموذج الأساسي لطلب التسجيل.

    Attributes:
        chat_id: معرف المستخدم في تيليجرام
        full_name: الاسم الكامل
        owner_phone: رقم هاتف المالك
        email: البريد الإلكتروني
        restaurant_name: اسم المطعم
        restaurant_type: نوع المطعم
        restaurant_phone: رقم هاتف المطعم
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
    """

    chat_id: int = Field(
        ...,
        description="معرف المستخدم في تيليجرام",
        json_schema_extra={"example": 123456789},
        ge=1,
    )
    full_name: str = Field(
        ...,
        max_length=255,
        description="الاسم الكامل",
        json_schema_extra={"example": "أحمد محمد"},
        min_length=2,
    )
    owner_phone: str = Field(
        ...,
        max_length=20,
        description="رقم هاتف المالك",
        json_schema_extra={"example": "0555123456"},
    )
    email: Optional[str] = Field(
        None,
        max_length=255,
        description="البريد الإلكتروني",
        json_schema_extra={"example": "ahmed@example.com"},
    )
    restaurant_name: str = Field(
        ...,
        max_length=255,
        description="اسم المطعم",
        json_schema_extra={"example": "مطعم البيتزا السريعة"},
        min_length=2,
    )
    restaurant_type: str = Field(
        ...,
        max_length=100,
        description="نوع المطعم",
        json_schema_extra={"example": "بيتزا"},
        min_length=2,
    )
    restaurant_phone: str = Field(
        ...,
        max_length=20,
        description="رقم هاتف المطعم",
        json_schema_extra={"example": "0555987654"},
    )
    wilaya: Optional[str] = Field(
        None,
        max_length=100,
        description="الولاية",
        json_schema_extra={"example": "Alger"},
    )
    lat: Optional[float] = Field(
        None,
        description="خط العرض",
        json_schema_extra={"example": 36.7538},
    )
    lng: Optional[float] = Field(
        None,
        description="خط الطول",
        json_schema_extra={"example": 3.0588},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة البريد الإلكتروني.

        Args:
            value: البريد الإلكتروني

        Returns:
            Optional[str]: البريد الإلكتروني المدقق

        Raises:
            ValueError: إذا كان البريد الإلكتروني غير صالح
        """
        if value is not None:
            if "@" not in value:
                raise ValueError("البريد الإلكتروني غير صالح")
            if "." not in value.split("@")[-1]:
                raise ValueError("البريد الإلكتروني غير صالح")
        return value

    # ==============================================
    # VALIDATE PHONE
    # ==============================================

    @field_validator("owner_phone", "restaurant_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        """
        التحقق من صحة رقم الهاتف.

        Args:
            value: رقم الهاتف

        Returns:
            str: رقم الهاتف المدقق

        Raises:
            ValueError: إذا كان رقم الهاتف غير صالح
        """
        # إزالة المسافات والشرطات
        cleaned = value.replace(" ", "").replace("-", "")

        if not cleaned.isdigit():
            raise ValueError("رقم الهاتف يجب أن يحتوي على أرقام فقط")

        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError("رقم الهاتف يجب أن يكون بين 10 و 15 رقماً")

        return cleaned


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class RegistrationRequestCreate(RegistrationRequestBase):
    """
    نموذج إنشاء طلب تسجيل جديد.

    وراثة من RegistrationRequestBase.
    """

    pass


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class RegistrationRequestUpdate(BaseModel):
    """
    نموذج تحديث طلب التسجيل - جميع الحقول اختيارية.

    Attributes:
        chat_id: معرف المستخدم في تيليجرام
        full_name: الاسم الكامل
        owner_phone: رقم هاتف المالك
        email: البريد الإلكتروني
        restaurant_name: اسم المطعم
        restaurant_type: نوع المطعم
        restaurant_phone: رقم هاتف المطعم
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        status: حالة الطلب (pending, approved, rejected)
        owner_id: معرف المالك المرتبط
    """

    chat_id: Optional[int] = Field(
        None,
        description="معرف المستخدم في تيليجرام",
        ge=1,
    )
    full_name: Optional[str] = Field(
        None,
        max_length=255,
        description="الاسم الكامل",
        min_length=2,
    )
    owner_phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم هاتف المالك",
    )
    email: Optional[str] = Field(
        None,
        max_length=255,
        description="البريد الإلكتروني",
    )
    restaurant_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم المطعم",
        min_length=2,
    )
    restaurant_type: Optional[str] = Field(
        None,
        max_length=100,
        description="نوع المطعم",
        min_length=2,
    )
    restaurant_phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم هاتف المطعم",
    )
    wilaya: Optional[str] = Field(
        None,
        max_length=100,
        description="الولاية",
    )
    lat: Optional[float] = Field(
        None,
        description="خط العرض",
    )
    lng: Optional[float] = Field(
        None,
        description="خط الطول",
    )
    status: Optional[str] = Field(
        None,
        max_length=50,
        description="حالة الطلب: pending, approved, rejected",
    )
    owner_id: Optional[int] = Field(
        None,
        description="معرف المالك المرتبط",
        ge=1,
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة البريد الإلكتروني.

        Args:
            value: البريد الإلكتروني

        Returns:
            Optional[str]: البريد الإلكتروني المدقق

        Raises:
            ValueError: إذا كان البريد الإلكتروني غير صالح
        """
        if value is not None:
            if "@" not in value:
                raise ValueError("البريد الإلكتروني غير صالح")
            if "." not in value.split("@")[-1]:
                raise ValueError("البريد الإلكتروني غير صالح")
        return value

    # ==============================================
    # VALIDATE PHONE
    # ==============================================

    @field_validator("owner_phone", "restaurant_phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة رقم الهاتف.

        Args:
            value: رقم الهاتف

        Returns:
            Optional[str]: رقم الهاتف المدقق

        Raises:
            ValueError: إذا كان رقم الهاتف غير صالح
        """
        if value is not None:
            cleaned = value.replace(" ", "").replace("-", "")

            if not cleaned.isdigit():
                raise ValueError("رقم الهاتف يجب أن يحتوي على أرقام فقط")

            if len(cleaned) < 10 or len(cleaned) > 15:
                raise ValueError("رقم الهاتف يجب أن يكون بين 10 و 15 رقماً")

            return cleaned
        return value


# ==============================================
# 📤 STATUS UPDATE SCHEMA
# ==============================================


class RegistrationRequestStatusUpdate(BaseModel):
    """
    نموذج تحديث حالة طلب التسجيل.

    Attributes:
        status: الحالة الجديدة (approved, rejected)
        note: ملاحظة إضافية
    """

    status: str = Field(
        ...,
        description="الحالة الجديدة: approved, rejected",
        json_schema_extra={"example": "approved"},
    )
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="ملاحظة إضافية",
        json_schema_extra={"example": "تم الموافقة على طلب التسجيل"},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        """
        التحقق من صحة الحالة.

        Args:
            value: الحالة

        Returns:
            str: الحالة المدققة

        Raises:
            ValueError: إذا كانت الحالة غير صالحة
        """
        valid_statuses = {"approved", "rejected"}
        if value not in valid_statuses:
            raise ValueError(
                f"الحالة يجب أن تكون واحدة من: {', '.join(valid_statuses)}"
            )
        return value


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class RegistrationRequestResponse(RegistrationRequestBase):
    """
    نموذج استجابة طلب التسجيل - يحتوي على جميع الحقول بما فيها التواريخ.

    Attributes:
        id: معرف طلب التسجيل
        status: حالة الطلب
        owner_id: معرف المالك المرتبط
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف طلب التسجيل",
        json_schema_extra={"example": 1},
        ge=1,
    )
    status: str = Field(
        ...,
        description="حالة الطلب: pending, approved, rejected",
        json_schema_extra={"example": "pending"},
    )
    owner_id: Optional[int] = Field(
        None,
        description="معرف المالك المرتبط",
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


# ==============================================
# 📋 LIST RESPONSE
# ==============================================


class RegistrationRequestListResponse(BaseModel):
    """
    مخطط استجابة قائمة طلبات التسجيل.

    يحتوي على قائمة طلبات التسجيل مع معلومات الترقيم.

    Attributes:
        items: قائمة طلبات التسجيل
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[RegistrationRequestResponse] = Field(
        ...,
        description="قائمة طلبات التسجيل",
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
# 📊 SUMMARY
# ==============================================


class RegistrationRequestSummary(BaseModel):
    """
    مخطط ملخص طلبات التسجيل.

    Attributes:
        total: إجمالي عدد الطلبات
        pending: عدد الطلبات المعلقة
        approved: عدد الطلبات المعتمدة
        rejected: عدد الطلبات المرفوضة
    """

    model_config = ConfigDict(from_attributes=True)

    total: int = Field(
        ...,
        description="إجمالي عدد الطلبات",
        json_schema_extra={"example": 100},
        ge=0,
    )
    pending: int = Field(
        ...,
        description="عدد الطلبات المعلقة",
        json_schema_extra={"example": 30},
        ge=0,
    )
    approved: int = Field(
        ...,
        description="عدد الطلبات المعتمدة",
        json_schema_extra={"example": 50},
        ge=0,
    )
    rejected: int = Field(
        ...,
        description="عدد الطلبات المرفوضة",
        json_schema_extra={"example": 20},
        ge=0,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RegistrationRequestBase",
    "RegistrationRequestCreate",
    "RegistrationRequestUpdate",
    "RegistrationRequestStatusUpdate",
    "RegistrationRequestResponse",
    "RegistrationRequestListResponse",
    "RegistrationRequestSummary",
    "RegistrationRequestData",
    "RegistrationRequestUpdateData",
    "RegistrationRequestListData",
]
