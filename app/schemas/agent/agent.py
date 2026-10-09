# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🤖 AGENT SCHEMAS
# مخططات Pydantic للوكيل الذكي
# ==============================================

"""MoulAI operational module for agent.

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

AgentData = Dict[str, Any]
AgentUpdateData = Dict[str, Any]
AgentListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class AgentBase(BaseModel):
    """
    المخطط الأساسي للوكيل.

    Attributes:
        restaurant_id: معرف المطعم
        name: اسم الوكيل
        description: وصف الوكيل
        language: اللغة (ar, fr, en)
        tone: النبرة (professional, casual, friendly)
        is_active: حالة النشاط
        config: إعدادات الوكيل
        ai_config: إعدادات الذكاء الاصطناعي
    """

    restaurant_id: int = Field(
        ...,
        description="معرف المطعم",
        json_schema_extra={"example": 1},
        ge=1,
    )
    name: str = Field(
        ...,
        max_length=100,
        description="اسم الوكيل",
        json_schema_extra={"example": "مساعدي الذكي"},
        min_length=1,
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="وصف الوكيل",
        json_schema_extra={"example": "وكيل ذكي لمطعم البيتزا السريعة"},
    )
    language: str = Field(
        "ar",
        max_length=10,
        description="اللغة: ar, fr, en",
        json_schema_extra={"example": "ar"},
    )
    tone: str = Field(
        "professional",
        max_length=50,
        description="النبرة: professional, casual, friendly",
        json_schema_extra={"example": "professional"},
    )
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="إعدادات الوكيل",
        json_schema_extra={
            "example": {
                "auto_reply": True,
                "upselling_enabled": True,
                "max_conversation_turns": 50,
            }
        },
    )
    ai_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="إعدادات الذكاء الاصطناعي",
        json_schema_extra={
            "example": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 500,
            }
        },
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        """
        التحقق من صحة اللغة.

        Args:
            value: اللغة

        Returns:
            str: اللغة المدققة

        Raises:
            ValueError: إذا كانت اللغة غير صالحة
        """
        valid_languages = {"ar", "fr", "en"}
        if value.lower() not in valid_languages:
            raise ValueError(
                f"اللغة يجب أن تكون واحدة من: {', '.join(valid_languages)}"
            )
        return value.lower()

    # ==============================================
    # VALIDATE TONE
    # ==============================================

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: str) -> str:
        """
        التحقق من صحة النبرة.

        Args:
            value: النبرة

        Returns:
            str: النبرة المدققة

        Raises:
            ValueError: إذا كانت النبرة غير صالحة
        """
        valid_tones = {"professional", "casual", "friendly"}
        if value.lower() not in valid_tones:
            raise ValueError(f"النبرة يجب أن تكون واحدة من: {', '.join(valid_tones)}")
        return value.lower()

    # ==============================================
    # VALIDATE NAME
    # ==============================================

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """
        التحقق من صحة اسم الوكيل.

        Args:
            value: اسم الوكيل

        Returns:
            str: اسم الوكيل المدقق

        Raises:
            ValueError: إذا كان الاسم غير صالح
        """
        if not value or not value.strip():
            raise ValueError("اسم الوكيل لا يمكن أن يكون فارغاً")
        return value.strip()


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class AgentCreate(AgentBase):
    """
    مخطط إنشاء وكيل جديد.

    يرث جميع حقول AgentBase.
    """

    pass


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class AgentUpdate(BaseModel):
    """
    مخطط تحديث الوكيل.

    Attributes:
        name: اسم الوكيل
        description: وصف الوكيل
        language: اللغة
        tone: النبرة
        is_active: حالة النشاط
        config: إعدادات الوكيل
        ai_config: إعدادات الذكاء الاصطناعي
    """

    name: Optional[str] = Field(
        None,
        max_length=100,
        description="اسم الوكيل",
        json_schema_extra={"example": "مساعدي الذكي"},
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="وصف الوكيل",
        json_schema_extra={"example": "وكيل ذكي لمطعم البيتزا السريعة"},
    )
    language: Optional[str] = Field(
        None,
        max_length=10,
        description="اللغة: ar, fr, en",
        json_schema_extra={"example": "ar"},
    )
    tone: Optional[str] = Field(
        None,
        max_length=50,
        description="النبرة: professional, casual, friendly",
        json_schema_extra={"example": "professional"},
    )
    is_active: Optional[bool] = Field(
        None,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="إعدادات الوكيل",
    )
    ai_config: Optional[Dict[str, Any]] = Field(
        None,
        description="إعدادات الذكاء الاصطناعي",
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة اللغة.

        Args:
            value: اللغة

        Returns:
            Optional[str]: اللغة المدققة

        Raises:
            ValueError: إذا كانت اللغة غير صالحة
        """
        if value is not None:
            valid_languages = {"ar", "fr", "en"}
            if value.lower() not in valid_languages:
                raise ValueError(
                    f"اللغة يجب أن تكون واحدة من: {', '.join(valid_languages)}"
                )
            return value.lower()
        return value

    # ==============================================
    # VALIDATE TONE
    # ==============================================

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة النبرة.

        Args:
            value: النبرة

        Returns:
            Optional[str]: النبرة المدققة

        Raises:
            ValueError: إذا كانت النبرة غير صالحة
        """
        if value is not None:
            valid_tones = {"professional", "casual", "friendly"}
            if value.lower() not in valid_tones:
                raise ValueError(
                    f"النبرة يجب أن تكون واحدة من: {', '.join(valid_tones)}"
                )
            return value.lower()
        return value

    # ==============================================
    # VALIDATE NAME
    # ==============================================

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة اسم الوكيل.

        Args:
            value: اسم الوكيل

        Returns:
            Optional[str]: اسم الوكيل المدقق

        Raises:
            ValueError: إذا كان الاسم غير صالح
        """
        if value is not None:
            if not value or not value.strip():
                raise ValueError("اسم الوكيل لا يمكن أن يكون فارغاً")
            return value.strip()
        return value


# ==============================================
# ⚙️ CONFIG UPDATE SCHEMA
# ==============================================


class AgentConfigUpdate(BaseModel):
    """
    مخطط تحديث إعدادات الوكيل.

    Attributes:
        config: إعدادات الوكيل
        ai_config: إعدادات الذكاء الاصطناعي
    """

    config: Optional[Dict[str, Any]] = Field(
        None,
        description="إعدادات الوكيل",
    )
    ai_config: Optional[Dict[str, Any]] = Field(
        None,
        description="إعدادات الذكاء الاصطناعي",
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class AgentResponse(AgentBase):
    """
    مخطط استجابة الوكيل.

    Attributes:
        id: معرف الوكيل
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الوكيل",
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


class AgentListResponse(BaseModel):
    """
    مخطط استجابة قائمة الوكلاء.

    Attributes:
        items: قائمة الوكلاء
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[AgentResponse] = Field(
        ...,
        description="قائمة الوكلاء",
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
# 📊 STATISTICS SCHEMA
# ==============================================


class AgentStatistics(BaseModel):
    """
    مخطط إحصائيات الوكيل.

    Attributes:
        total_agents: إجمالي عدد الوكلاء
        active_agents: عدد الوكلاء النشطين
        inactive_agents: عدد الوكلاء غير النشطين
        language_distribution: توزيع اللغات
        tone_distribution: توزيع النبرات
    """

    model_config = ConfigDict(from_attributes=True)

    total_agents: int = Field(
        ...,
        description="إجمالي عدد الوكلاء",
        json_schema_extra={"example": 5},
        ge=0,
    )
    active_agents: int = Field(
        ...,
        description="عدد الوكلاء النشطين",
        json_schema_extra={"example": 3},
        ge=0,
    )
    inactive_agents: int = Field(
        ...,
        description="عدد الوكلاء غير النشطين",
        json_schema_extra={"example": 2},
        ge=0,
    )
    language_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="توزيع اللغات",
        json_schema_extra={"example": {"ar": 3, "en": 1, "fr": 1}},
    )
    tone_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="توزيع النبرات",
        json_schema_extra={"example": {"professional": 3, "casual": 1, "friendly": 1}},
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "AgentBase",
    "AgentCreate",
    "AgentUpdate",
    "AgentConfigUpdate",
    "AgentResponse",
    "AgentListResponse",
    "AgentStatistics",
    "AgentData",
    "AgentUpdateData",
    "AgentListData",
]
