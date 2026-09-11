# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👤 USER SCHEMAS
# نماذج Pydantic للمستخدمين
# تدير التحقق من صحة البيانات وتسلسلها للمستخدمين
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

UserData = Dict[str, Any]
UserUpdateData = Dict[str, Any]
UserList = List["UserResponse"]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class UserBase(BaseModel):
    """
    المخطط الأساسي للمستخدم.
    
    يحتوي على الحقول المشتركة بين جميع مخططات المستخدم.
    
    Attributes:
        chat_id: معرف المستخدم في تيليجرام
        consent: موافقة المستخدم على الشروط والأحكام
        customer_name: اسم العميل
        customer_phone: رقم هاتف العميل
    """
    chat_id: Optional[int] = Field(
        None,
        description="معرف المستخدم في تيليجرام",
        json_schema_extra={"example": 123456789},
    )
    consent: bool = Field(
        False,
        description="موافقة المستخدم على الشروط والأحكام",
        json_schema_extra={"example": True},
    )
    customer_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم العميل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    customer_phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم هاتف العميل",
        json_schema_extra={"example": "0555123456"},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class UserCreate(BaseModel):
    """
    مخطط إنشاء مستخدم جديد.
    
    Attributes:
        chat_id: معرف المستخدم في تيليجرام
        consent: موافقة المستخدم (اختياري)
        customer_name: اسم العميل (اختياري)
        customer_phone: رقم هاتف العميل (اختياري)
    """
    chat_id: int = Field(
        ...,
        description="معرف المستخدم في تيليجرام",
        json_schema_extra={"example": 123456789},
    )
    consent: bool = Field(
        False,
        description="موافقة المستخدم على الشروط والأحكام",
        json_schema_extra={"example": True},
    )
    customer_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم العميل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    customer_phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم هاتف العميل",
        json_schema_extra={"example": "0555123456"},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class UserUpdate(BaseModel):
    """
    مخطط تحديث المستخدم - جميع الحقول اختيارية.
    
    Attributes:
        consent: موافقة المستخدم
        customer_name: اسم العميل
        customer_phone: رقم هاتف العميل
    """
    consent: Optional[bool] = Field(
        None,
        description="موافقة المستخدم على الشروط والأحكام",
        json_schema_extra={"example": True},
    )
    customer_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم العميل",
        json_schema_extra={"example": "أحمد محمد"},
    )
    customer_phone: Optional[str] = Field(
        None,
        max_length=20,
        description="رقم هاتف العميل",
        json_schema_extra={"example": "0555123456"},
    )


# ==============================================
# ✅ CONSENT UPDATE SCHEMA
# ==============================================

class UserConsentUpdate(BaseModel):
    """
    مخطط تحديث موافقة المستخدم.
    
    Attributes:
        consent: حالة الموافقة الجديدة
    """
    consent: bool = Field(
        ...,
        description="حالة الموافقة الجديدة",
        json_schema_extra={"example": True},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class UserResponse(UserBase):
    """
    مخطط استجابة المستخدم - يحتوي على جميع الحقول بما فيها التواريخ.
    
    Attributes:
        id: معرف المستخدم
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف المستخدم",
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
# 📋 USER LIST RESPONSE
# ==============================================

class UserListResponse(BaseModel):
    """
    مخطط استجابة قائمة المستخدمين.
    
    Attributes:
        items: قائمة المستخدمين
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: UserList = Field(
        ...,
        description="قائمة المستخدمين",
    )
    total: int = Field(
        ...,
        description="العدد الإجمالي",
        json_schema_extra={"example": 10},
    )
    skip: int = Field(
        ...,
        description="عدد السجلات المتخطية",
        json_schema_extra={"example": 0},
    )
    limit: int = Field(
        ...,
        description="الحد الأقصى للسجلات",
        json_schema_extra={"example": 100},
    )


# ==============================================
# 📊 USER SUMMARY
# ==============================================

class UserSummary(BaseModel):
    """
    مخطط ملخص المستخدمين.
    
    Attributes:
        total_users: إجمالي عدد المستخدمين
        users_with_consent: عدد المستخدمين بالموافقة
        users_without_consent: عدد المستخدمين بدون موافقة
        users_with_name: عدد المستخدمين بالاسم
        users_with_phone: عدد المستخدمين برقم الهاتف
        consent_rate: نسبة الموافقة
        profile_completion_rate: نسبة اكتمال الملف الشخصي
    """
    model_config = ConfigDict(from_attributes=True)

    total_users: int = Field(
        ...,
        description="إجمالي عدد المستخدمين",
        json_schema_extra={"example": 100},
    )
    users_with_consent: int = Field(
        ...,
        description="عدد المستخدمين بالموافقة",
        json_schema_extra={"example": 80},
    )
    users_without_consent: int = Field(
        ...,
        description="عدد المستخدمين بدون موافقة",
        json_schema_extra={"example": 20},
    )
    users_with_name: int = Field(
        ...,
        description="عدد المستخدمين بالاسم",
        json_schema_extra={"example": 70},
    )
    users_with_phone: int = Field(
        ...,
        description="عدد المستخدمين برقم الهاتف",
        json_schema_extra={"example": 60},
    )
    consent_rate: float = Field(
        ...,
        description="نسبة الموافقة (%)",
        json_schema_extra={"example": 80.0},
    )
    profile_completion_rate: float = Field(
        ...,
        description="نسبة اكتمال الملف الشخصي (%)",
        json_schema_extra={"example": 65.0},
    )


# ==============================================
# 🔍 USER SEARCH
# ==============================================

class UserSearch(BaseModel):
    """
    مخطط البحث عن المستخدمين.
    
    Attributes:
        query: نص البحث
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    query: str = Field(
        ...,
        min_length=1,
        description="نص البحث (الاسم أو رقم الهاتف)",
        json_schema_extra={"example": "أحمد"},
    )
    skip: int = Field(
        0,
        ge=0,
        description="عدد السجلات المتخطية",
        json_schema_extra={"example": 0},
    )
    limit: int = Field(
        100,
        ge=1,
        le=100,
        description="الحد الأقصى للسجلات",
        json_schema_extra={"example": 10},
    )


# ==============================================
# ✅ CONSENT RESPONSE
# ==============================================

class ConsentResponse(BaseModel):
    """
    مخطط استجابة الموافقة.
    
    Attributes:
        chat_id: معرف المستخدم
        has_consent: حالة الموافقة
        message: رسالة توضيحية
    """
    model_config = ConfigDict(from_attributes=True)

    chat_id: int = Field(
        ...,
        description="معرف المستخدم في تيليجرام",
        json_schema_extra={"example": 123456789},
    )
    has_consent: bool = Field(
        ...,
        description="حالة الموافقة",
        json_schema_extra={"example": True},
    )
    message: str = Field(
        ...,
        description="رسالة توضيحية",
        json_schema_extra={"example": "User has given consent"},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserConsentUpdate",
    "UserResponse",
    "UserListResponse",
    "UserSummary",
    "UserSearch",
    "ConsentResponse",
    "UserData",
    "UserUpdateData",
    "UserList",
]