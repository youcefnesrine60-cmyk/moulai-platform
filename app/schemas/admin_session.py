# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔐 ADMIN SESSION SCHEMAS
# نماذج Pydantic لجلسات المديرين
# ==============================================

"""MoulAI operational module for admin session.

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

AdminSessionData = Dict[str, Any]
AdminSessionUpdateData = Dict[str, Any]
AdminSessionListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class AdminSessionBase(BaseModel):
    """
    المخطط الأساسي لجلسة المدير.

    Attributes:
        admin_id: معرف المدير
        session_token: رمز الجلسة
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المدير (اختياري)
        expires_at: تاريخ انتهاء الجلسة
        is_active: حالة النشاط
        last_activity: تاريخ آخر نشاط
    """

    admin_id: int = Field(
        ...,
        description="معرف المدير",
        json_schema_extra={"example": 1},
        ge=1,
    )
    session_token: str = Field(
        ...,
        max_length=255,
        description="رمز الجلسة",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    ip_address: Optional[str] = Field(
        None,
        max_length=45,
        description="عنوان IP",
        json_schema_extra={"example": "192.168.1.1"},
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="متصفح المدير",
        json_schema_extra={"example": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    expires_at: datetime = Field(
        ...,
        description="تاريخ انتهاء الجلسة",
    )
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )
    last_activity: datetime = Field(
        ...,
        description="تاريخ آخر نشاط",
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime) -> datetime:
        """
        التحقق من أن تاريخ الانتهاء في المستقبل.

        Args:
            value: تاريخ الانتهاء

        Returns:
            datetime: تاريخ الانتهاء المدقق

        Raises:
            ValueError: إذا كان التاريخ في الماضي
        """
        if value <= datetime.now():
            raise ValueError("تاريخ انتهاء الجلسة يجب أن يكون في المستقبل")
        return value

    # ==============================================
    # VALIDATE SESSION TOKEN
    # ==============================================

    @field_validator("session_token")
    @classmethod
    def validate_session_token(cls, value: str) -> str:
        """
        التحقق من صحة رمز الجلسة.

        Args:
            value: رمز الجلسة

        Returns:
            str: رمز الجلسة المدقق

        Raises:
            ValueError: إذا كان رمز الجلسة فارغاً
        """
        if not value or not value.strip():
            raise ValueError("رمز الجلسة لا يمكن أن يكون فارغاً")
        return value.strip()


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class AdminSessionCreate(BaseModel):
    """
    مخطط إنشاء جلسة مدير جديدة.

    Attributes:
        admin_id: معرف المدير
        expires_at: تاريخ انتهاء الجلسة
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المدير (اختياري)
    """

    admin_id: int = Field(
        ...,
        description="معرف المدير",
        json_schema_extra={"example": 1},
        ge=1,
    )
    expires_at: datetime = Field(
        ...,
        description="تاريخ انتهاء الجلسة",
    )
    ip_address: Optional[str] = Field(
        None,
        max_length=45,
        description="عنوان IP (اختياري)",
        json_schema_extra={"example": "192.168.1.1"},
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="متصفح المدير (اختياري)",
        json_schema_extra={"example": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime) -> datetime:
        """
        التحقق من أن تاريخ الانتهاء في المستقبل.

        Args:
            value: تاريخ الانتهاء

        Returns:
            datetime: تاريخ الانتهاء المدقق

        Raises:
            ValueError: إذا كان التاريخ في الماضي
        """
        if value <= datetime.now():
            raise ValueError("تاريخ انتهاء الجلسة يجب أن يكون في المستقبل")
        return value


# ==============================================
# 📤 EXTEND SCHEMA
# ==============================================


class AdminSessionExtend(BaseModel):
    """
    مخطط تمديد صلاحية الجلسة.

    Attributes:
        session_token: رمز الجلسة
        expires_at: تاريخ الانتهاء الجديد
    """

    session_token: str = Field(
        ...,
        max_length=255,
        description="رمز الجلسة",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    expires_at: datetime = Field(
        ...,
        description="تاريخ الانتهاء الجديد",
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, value: datetime) -> datetime:
        """
        التحقق من أن تاريخ الانتهاء في المستقبل.

        Args:
            value: تاريخ الانتهاء

        Returns:
            datetime: تاريخ الانتهاء المدقق

        Raises:
            ValueError: إذا كان التاريخ في الماضي
        """
        if value <= datetime.now():
            raise ValueError("تاريخ انتهاء الجلسة يجب أن يكون في المستقبل")
        return value

    # ==============================================
    # VALIDATE SESSION TOKEN
    # ==============================================

    @field_validator("session_token")
    @classmethod
    def validate_session_token(cls, value: str) -> str:
        """
        التحقق من صحة رمز الجلسة.

        Args:
            value: رمز الجلسة

        Returns:
            str: رمز الجلسة المدقق

        Raises:
            ValueError: إذا كان رمز الجلسة فارغاً
        """
        if not value or not value.strip():
            raise ValueError("رمز الجلسة لا يمكن أن يكون فارغاً")
        return value.strip()


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class AdminSessionResponse(AdminSessionBase):
    """
    مخطط استجابة جلسة المدير.

    Attributes:
        id: معرف الجلسة
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الجلسة",
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


class AdminSessionListResponse(BaseModel):
    """
    مخطط استجابة قائمة جلسات المدير.

    Attributes:
        items: قائمة جلسات المدير
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[AdminSessionResponse] = Field(
        ...,
        description="قائمة جلسات المدير",
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
# 📊 SESSION STATISTICS
# ==============================================


class AdminSessionStatistics(BaseModel):
    """
    مخطط إحصائيات جلسات المدير.

    Attributes:
        total_sessions: إجمالي عدد الجلسات
        active_sessions: عدد الجلسات النشطة
        expired_sessions: عدد الجلسات المنتهية
        admin_id: معرف المدير (اختياري)
    """

    model_config = ConfigDict(from_attributes=True)

    total_sessions: int = Field(
        ...,
        description="إجمالي عدد الجلسات",
        json_schema_extra={"example": 10},
        ge=0,
    )
    active_sessions: int = Field(
        ...,
        description="عدد الجلسات النشطة",
        json_schema_extra={"example": 5},
        ge=0,
    )
    expired_sessions: int = Field(
        ...,
        description="عدد الجلسات المنتهية",
        json_schema_extra={"example": 5},
        ge=0,
    )
    admin_id: Optional[int] = Field(
        None,
        description="معرف المدير (اختياري)",
        json_schema_extra={"example": 1},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "AdminSessionBase",
    "AdminSessionCreate",
    "AdminSessionExtend",
    "AdminSessionResponse",
    "AdminSessionListResponse",
    "AdminSessionStatistics",
    "AdminSessionData",
    "AdminSessionUpdateData",
    "AdminSessionListData",
]
