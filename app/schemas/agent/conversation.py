# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 💬 CONVERSATION SCHEMAS
# مخططات Pydantic للمحادثات
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
    field_validator,
)


# ==============================================
# 🧩 TYPES
# ==============================================

ConversationData = Dict[str, Any]
ConversationUpdateData = Dict[str, Any]
ConversationListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class ConversationBase(BaseModel):
    """
    المخطط الأساسي للمحادثة.
    
    Attributes:
        agent_id: معرف الوكيل
        channel_id: معرف القناة
        user_id: معرف المستخدم
        user_name: اسم المستخدم
        status: حالة المحادثة (active, closed, suspended)
        is_active: حالة النشاط
        context: سياق المحادثة
    """
    agent_id: int = Field(
        ...,
        description="معرف الوكيل",
        json_schema_extra={"example": 1},
        ge=1,
    )
    channel_id: int = Field(
        ...,
        description="معرف القناة",
        json_schema_extra={"example": 1},
        ge=1,
    )
    user_id: str = Field(
        ...,
        max_length=255,
        description="معرف المستخدم من القناة (chat_id)",
        json_schema_extra={"example": "123456789"},
        min_length=1,
    )
    user_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم المستخدم",
        json_schema_extra={"example": "أحمد محمد"},
    )
    status: str = Field(
        "active",
        max_length=20,
        description="حالة المحادثة: active, closed, suspended",
        json_schema_extra={"example": "active"},
    )
    is_active: bool = Field(
        True,
        description="حالة النشاط",
        json_schema_extra={"example": True},
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="سياق المحادثة",
        json_schema_extra={
            "example": {
                "current_order": None,
                "current_step": None,
                "intent_history": [],
                "last_intent": "greeting",
                "entities": {},
            }
        },
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        """
        التحقق من صحة حالة المحادثة.
        
        Args:
            value: حالة المحادثة
            
        Returns:
            str: حالة المحادثة المدققة
            
        Raises:
            ValueError: إذا كانت الحالة غير صالحة
        """
        valid_statuses = {"active", "closed", "suspended"}
        if value.lower() not in valid_statuses:
            raise ValueError(
                f"حالة المحادثة يجب أن تكون واحدة من: {', '.join(valid_statuses)}"
            )
        return value.lower()

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        """
        التحقق من صحة معرف المستخدم.
        
        Args:
            value: معرف المستخدم
            
        Returns:
            str: معرف المستخدم المدقق
            
        Raises:
            ValueError: إذا كان المعرف غير صالح
        """
        if not value or not value.strip():
            raise ValueError("معرف المستخدم لا يمكن أن يكون فارغاً")
        return value.strip()


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class ConversationCreate(ConversationBase):
    """
    مخطط إنشاء محادثة جديدة.
    """
    pass


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================

class ConversationUpdate(BaseModel):
    """
    مخطط تحديث المحادثة.
    
    Attributes:
        user_name: اسم المستخدم
        status: حالة المحادثة
        is_active: حالة النشاط
        context: سياق المحادثة
    """
    user_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم المستخدم",
        json_schema_extra={"example": "أحمد محمد"},
    )
    status: Optional[str] = Field(
        None,
        max_length=20,
        description="حالة المحادثة: active, closed, suspended",
        json_schema_extra={"example": "closed"},
    )
    is_active: Optional[bool] = Field(
        None,
        description="حالة النشاط",
        json_schema_extra={"example": False},
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="سياق المحادثة",
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة حالة المحادثة.
        
        Args:
            value: حالة المحادثة
            
        Returns:
            Optional[str]: حالة المحادثة المدققة
            
        Raises:
            ValueError: إذا كانت الحالة غير صالحة
        """
        if value is not None:
            valid_statuses = {"active", "closed", "suspended"}
            if value.lower() not in valid_statuses:
                raise ValueError(
                    f"حالة المحادثة يجب أن تكون واحدة من: {', '.join(valid_statuses)}"
                )
            return value.lower()
        return value


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class ConversationResponse(ConversationBase):
    """
    مخطط استجابة المحادثة.
    
    Attributes:
        id: معرف المحادثة
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف المحادثة",
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

class ConversationListResponse(BaseModel):
    """
    مخطط استجابة قائمة المحادثات.
    
    Attributes:
        items: قائمة المحادثات
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[ConversationResponse] = Field(
        ...,
        description="قائمة المحادثات",
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

class ConversationStatistics(BaseModel):
    """
    مخطط إحصائيات المحادثات.
    
    Attributes:
        total_conversations: إجمالي عدد المحادثات
        active_conversations: عدد المحادثات النشطة
        inactive_conversations: عدد المحادثات غير النشطة
        status_summary: ملخص حالات المحادثات
    """
    model_config = ConfigDict(from_attributes=True)

    total_conversations: int = Field(
        ...,
        description="إجمالي عدد المحادثات",
        json_schema_extra={"example": 100},
        ge=0,
    )
    active_conversations: int = Field(
        ...,
        description="عدد المحادثات النشطة",
        json_schema_extra={"example": 80},
        ge=0,
    )
    inactive_conversations: int = Field(
        ...,
        description="عدد المحادثات غير النشطة",
        json_schema_extra={"example": 20},
        ge=0,
    )
    status_summary: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="ملخص حالات المحادثات",
        json_schema_extra={
            "example": [
                {"status": "active", "count": 80},
                {"status": "closed", "count": 15},
                {"status": "suspended", "count": 5},
            ]
        },
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "ConversationBase",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationListResponse",
    "ConversationStatistics",
    "ConversationData",
    "ConversationUpdateData",
    "ConversationListData",
]