# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🍽️ RESTAURANT SCHEMAS
# نماذج Pydantic للمطاعم
# تدير التحقق من صحة البيانات وتسلسلها للمطاعم
# ==============================================

"""MoulAI operational module for restaurant.

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

RestaurantData = Dict[str, Any]
RestaurantUpdateData = Dict[str, Any]
RestaurantListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class RestaurantBase(BaseModel):
    """
    المخطط الأساسي للمطعم.

    يحتوي على الحقول المشتركة بين جميع مخططات المطعم.

    Attributes:
        owner_id: معرف المالك
        group_id: معرف المجموعة
        name: اسم المطعم
        type: نوع المطعم
        phone: رقم الهاتف
        wilaya: الولاية (اختياري)
        lat: خط العرض (اختياري)
        lng: خط الطول (اختياري)
        is_active: حالة النشاط
    """

    owner_id: int = Field(
        ...,
        description="معرف المالك",
        json_schema_extra={"example": 1},
        ge=1,
    )
    group_id: Optional[int] = Field(
        None,
        description="معرف المجموعة",
        json_schema_extra={"example": 1},
    )
    name: str = Field(
        ...,
        max_length=255,
        description="اسم المطعم",
        json_schema_extra={"example": "مطعم البيتزا السريعة"},
        min_length=2,
    )
    type: str = Field(
        ...,
        max_length=100,
        description="نوع المطعم",
        json_schema_extra={"example": "pizza"},
        min_length=2,
    )
    phone: str = Field(
        ...,
        max_length=20,
        description="رقم الهاتف",
        json_schema_extra={"example": "0555123456"},
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
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        """
        التحقق من صحة رقم الهاتف.

        ✅ السماح بـ + في البداية

        Args:
            value: رقم الهاتف

        Returns:
            str: رقم الهاتف المدقق

        Raises:
            ValueError: إذا كان رقم الهاتف غير صالح
        """
        # إزالة المسافات والشرطات
        cleaned = value.replace(" ", "").replace("-", "")

        # إزالة + للتحقق
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]

        if not cleaned.isdigit():
            raise ValueError("رقم الهاتف يجب أن يحتوي على أرقام فقط")

        if len(cleaned) < 9 or len(cleaned) > 15:
            raise ValueError("رقم الهاتف يجب أن يكون بين 09 و 15 رقماً")

        # إرجاع الرقم مع + إذا كان موجوداً
        return value if value.startswith("+") else cleaned

    # ==============================================
    # VALIDATE TYPE
    # ==============================================

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        """
        التحقق من صحة نوع المطعم.

        Args:
            value: نوع المطعم

        Returns:
            str: نوع المطعم المدقق

        Raises:
            ValueError: إذا كان النوع غير صالح
        """
        valid_types = {"restaurant", "cafe", "fast_food", "bakery", "pizza", "other"}
        if value.lower() not in valid_types:
            raise ValueError(
                f"نوع المطعم يجب أن يكون واحداً من: {', '.join(valid_types)}"
            )
        return value.lower()


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class RestaurantCreate(RestaurantBase):
    """
    مخطط إنشاء مطعم جديد.

    يرث جميع حقول RestaurantBase.
    """

    pass


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class RestaurantUpdate(BaseModel):
    """
    مخطط تحديث مطعم - جميع الحقول اختيارية.

    Attributes:
        owner_id: معرف المالك
        group_id: معرف المجموعة
        name: اسم المطعم
        type: نوع المطعم
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        is_active: حالة النشاط
    """

    owner_id: Optional[int] = Field(
        None,
        description="معرف المالك",
        ge=1,
    )
    group_id: Optional[int] = Field(
        None,
        description="معرف المجموعة",
    )
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم المطعم",
        min_length=2,
    )
    type: Optional[str] = Field(
        None,
        max_length=100,
        description="نوع المطعم",
        min_length=2,
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم الهاتف",
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
    is_active: Optional[bool] = Field(
        None,
        description="حالة النشاط",
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة رقم الهاتف.

        ✅ السماح بـ + في البداية

        Args:
            value: رقم الهاتف

        Returns:
            Optional[str]: رقم الهاتف المدقق

        Raises:
            ValueError: إذا كان رقم الهاتف غير صالح
        """
        if value is not None:
            # إزالة المسافات والشرطات
            cleaned = value.replace(" ", "").replace("-", "")

            # إزالة + للتحقق
            if cleaned.startswith("+"):
                cleaned = cleaned[1:]

            if not cleaned.isdigit():
                raise ValueError("رقم الهاتف يجب أن يحتوي على أرقام فقط")

            if len(cleaned) < 9 or len(cleaned) > 15:
                raise ValueError("رقم الهاتف يجب أن يكون بين 09 و 15 رقماً")

            # إرجاع الرقم مع + إذا كان موجوداً
            return value if value.startswith("+") else cleaned
        return value

    # ==============================================
    # VALIDATE TYPE
    # ==============================================

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة نوع المطعم.

        Args:
            value: نوع المطعم

        Returns:
            Optional[str]: نوع المطعم المدقق

        Raises:
            ValueError: إذا كان النوع غير صالح
        """
        if value is not None:
            valid_types = {
                "restaurant",
                "cafe",
                "fast_food",
                "bakery",
                "pizza",
                "other",
            }
            if value.lower() not in valid_types:
                raise ValueError(
                    f"نوع المطعم يجب أن يكون واحداً من: {', '.join(valid_types)}"
                )
            return value.lower()
        return value


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class RestaurantResponse(RestaurantBase):
    """
    مخطط استجابة المطعم.

    يحتوي على جميع حقول المطعم مع الحقول الإضافية للاستجابة.

    Attributes:
        id: معرف المطعم
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف المطعم",
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


class RestaurantListResponse(BaseModel):
    """
    مخطط استجابة قائمة المطاعم.

    يحتوي على قائمة المطاعم مع معلومات الترقيم.

    Attributes:
        items: قائمة المطاعم
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[RestaurantResponse] = Field(
        ...,
        description="قائمة المطاعم",
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
# 📊 STATS SCHEMA
# ==============================================


class RestaurantStats(BaseModel):
    """
    مخطط إحصائيات المطعم.

    يحتوي على إحصائيات ومعلومات موجزة عن المطعم.

    Attributes:
        total_restaurants: إجمالي عدد المطاعم
        active_restaurants: عدد المطاعم النشطة
        inactive_restaurants: عدد المطاعم غير النشطة
        type_distribution: توزيع المطاعم حسب النوع
        wilaya_distribution: توزيع المطاعم حسب الولاية
    """

    model_config = ConfigDict(from_attributes=True)

    total_restaurants: int = Field(
        ...,
        description="إجمالي عدد المطاعم",
        json_schema_extra={"example": 10},
        ge=0,
    )
    active_restaurants: int = Field(
        ...,
        description="عدد المطاعم النشطة",
        json_schema_extra={"example": 8},
        ge=0,
    )
    inactive_restaurants: int = Field(
        ...,
        description="عدد المطاعم غير النشطة",
        json_schema_extra={"example": 2},
        ge=0,
    )
    type_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="توزيع المطاعم حسب النوع",
        json_schema_extra={"example": {"pizza": 3, "fast_food": 2, "restaurant": 5}},
    )
    wilaya_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="توزيع المطاعم حسب الولاية",
        json_schema_extra={"example": {"Alger": 4, "Oran": 3, "Constantine": 3}},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantBase",
    "RestaurantCreate",
    "RestaurantUpdate",
    "RestaurantResponse",
    "RestaurantListResponse",
    "RestaurantStats",
    "RestaurantData",
    "RestaurantUpdateData",
    "RestaurantListData",
]
