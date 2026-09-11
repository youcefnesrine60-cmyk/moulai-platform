# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📋 ADMIN LOG SCHEMAS
# نماذج Pydantic لسجل أنشطة المديرين
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

AdminLogData = Dict[str, Any]
AdminLogUpdateData = Dict[str, Any]
AdminLogListData = List[Dict[str, Any]]


# ==============================================
# 📦 BASE SCHEMA
# ==============================================

class AdminLogBase(BaseModel):
    """
    المخطط الأساسي لسجل أنشطة المدير.
    
    Attributes:
        admin_id: معرف المدير
        action: نوع الإجراء
        resource: نوع المورد (اختياري)
        resource_id: معرف المورد (اختياري)
        details: تفاصيل إضافية (اختياري)
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المدير (اختياري)
    """
    admin_id: int = Field(
        ...,
        description="معرف المدير",
        json_schema_extra={"example": 1},
        ge=1,
    )
    action: str = Field(
        ...,
        max_length=50,
        description="نوع الإجراء",
        json_schema_extra={"example": "login"},
    )
    resource: Optional[str] = Field(
        None,
        max_length=50,
        description="نوع المورد",
        json_schema_extra={"example": "admin"},
    )
    resource_id: Optional[int] = Field(
        None,
        description="معرف المورد",
        json_schema_extra={"example": 1},
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="تفاصيل إضافية (كائن JSON)",
        json_schema_extra={"example": {"reason": "تسجيل الدخول من جهاز جديد"}},
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

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        """
        التحقق من صحة نوع الإجراء.
        
        Args:
            value: نوع الإجراء
            
        Returns:
            str: نوع الإجراء بعد التحقق
            
        Raises:
            ValueError: إذا كان نوع الإجراء غير صحيح
        """
        allowed_actions = {
            "login",
            "logout",
            "create",
            "update",
            "delete",
            "view",
            "approve",
            "reject",
            "export",
            "import",
            "settings",
            "permission",
            "password",
            "reset",
            "lock",
            "unlock",
        }

        if value and value.lower() not in allowed_actions:
            raise ValueError(
                f"نوع الإجراء يجب أن يكون أحد القيم التالية: "
                f"{', '.join(sorted(allowed_actions))}"
            )

        return value.lower()


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================

class AdminLogCreate(BaseModel):
    """
    مخطط إنشاء سجل نشاط جديد.
    
    Attributes:
        admin_id: معرف المدير
        action: نوع الإجراء
        resource: نوع المورد (اختياري)
        resource_id: معرف المورد (اختياري)
        details: تفاصيل إضافية (اختياري)
        ip_address: عنوان IP (اختياري)
        user_agent: متصفح المدير (اختياري)
    """
    admin_id: int = Field(
        ...,
        description="معرف المدير",
        json_schema_extra={"example": 1},
        ge=1,
    )
    action: str = Field(
        ...,
        max_length=50,
        description="نوع الإجراء",
        json_schema_extra={"example": "login"},
    )
    resource: Optional[str] = Field(
        None,
        max_length=50,
        description="نوع المورد",
        json_schema_extra={"example": "admin"},
    )
    resource_id: Optional[int] = Field(
        None,
        description="معرف المورد",
        json_schema_extra={"example": 1},
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        max_length=1000,
        description="تفاصيل إضافية (كائن JSON)",
        json_schema_extra={"example": {"reason": "تسجيل الدخول من جهاز جديد"}},
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

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        """
        التحقق من صحة نوع الإجراء.
        
        Args:
            value: نوع الإجراء
            
        Returns:
            str: نوع الإجراء بعد التحقق
            
        Raises:
            ValueError: إذا كان نوع الإجراء غير صحيح
        """
        allowed_actions = {
            "login",
            "logout",
            "create",
            "update",
            "delete",
            "view",
            "approve",
            "reject",
            "export",
            "import",
            "settings",
            "permission",
            "password",
            "reset",
            "lock",
            "unlock",
        }

        if value and value.lower() not in allowed_actions:
            raise ValueError(
                f"نوع الإجراء يجب أن يكون أحد القيم التالية: "
                f"{', '.join(sorted(allowed_actions))}"
            )

        return value.lower()


# ==============================================
# 📤 FILTER SCHEMA
# ==============================================

class AdminLogFilter(BaseModel):
    """
    مخطط تصفية سجل الأنشطة.
    
    Attributes:
        action: نوع الإجراء (اختياري)
        resource: نوع المورد (اختياري)
        start_date: تاريخ البداية (اختياري)
        end_date: تاريخ النهاية (اختياري)
    """
    action: Optional[str] = Field(
        None,
        max_length=50,
        description="نوع الإجراء",
        json_schema_extra={"example": "login"},
    )
    resource: Optional[str] = Field(
        None,
        max_length=50,
        description="نوع المورد",
        json_schema_extra={"example": "admin"},
    )
    start_date: Optional[datetime] = Field(
        None,
        description="تاريخ البداية",
    )
    end_date: Optional[datetime] = Field(
        None,
        description="تاريخ النهاية",
    )

    # ==========================================
    # 🔍 VALIDATORS
    # ==========================================

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: Optional[str]) -> Optional[str]:
        """
        التحقق من صحة نوع الإجراء.
        
        Args:
            value: نوع الإجراء
            
        Returns:
            Optional[str]: نوع الإجراء بعد التحقق
            
        Raises:
            ValueError: إذا كان نوع الإجراء غير صحيح
        """
        if value is None:
            return value

        allowed_actions = {
            "login",
            "logout",
            "create",
            "update",
            "delete",
            "view",
            "approve",
            "reject",
            "export",
            "import",
            "settings",
            "permission",
            "password",
            "reset",
            "lock",
            "unlock",
        }

        if value.lower() not in allowed_actions:
            raise ValueError(
                f"نوع الإجراء يجب أن يكون أحد القيم التالية: "
                f"{', '.join(sorted(allowed_actions))}"
            )

        return value.lower()


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================

class AdminLogResponse(AdminLogBase):
    """
    مخطط استجابة سجل النشاط.
    
    Attributes:
        id: معرف سجل النشاط
        timestamp: تاريخ النشاط
        created_at: تاريخ الإنشاء
    """
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف سجل النشاط",
        json_schema_extra={"example": 1},
        ge=1,
    )
    timestamp: datetime = Field(
        ...,
        description="تاريخ النشاط",
    )
    created_at: datetime = Field(
        ...,
        description="تاريخ الإنشاء",
    )


# ==============================================
# 📋 LIST RESPONSE
# ==============================================

class AdminLogListResponse(BaseModel):
    """
    مخطط استجابة قائمة سجل الأنشطة.
    
    Attributes:
        items: قائمة سجل الأنشطة
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[AdminLogResponse] = Field(
        ...,
        description="قائمة سجل الأنشطة",
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
# 📊 ACTIONS SUMMARY
# ==============================================

class ActionSummary(BaseModel):
    """
    مخطط ملخص الإجراءات.
    
    Attributes:
        action: نوع الإجراء
        count: عدد مرات تكرار الإجراء
    """
    model_config = ConfigDict(from_attributes=True)

    action: str = Field(
        ...,
        description="نوع الإجراء",
        json_schema_extra={"example": "login"},
    )
    count: int = Field(
        ...,
        description="عدد مرات تكرار الإجراء",
        json_schema_extra={"example": 10},
        ge=0,
    )


class ActionsSummaryResponse(BaseModel):
    """
    مخطط استجابة ملخص الإجراءات.
    
    Attributes:
        items: قائمة ملخص الإجراءات
        total: العدد الإجمالي
    """
    model_config = ConfigDict(from_attributes=True)

    items: List[ActionSummary] = Field(
        ...,
        description="قائمة ملخص الإجراءات",
    )
    total: int = Field(
        ...,
        description="العدد الإجمالي",
        json_schema_extra={"example": 10},
        ge=0,
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "AdminLogBase",
    "AdminLogCreate",
    "AdminLogFilter",
    "AdminLogResponse",
    "AdminLogListResponse",
    "ActionSummary",
    "ActionsSummaryResponse",
    "AdminLogData",
    "AdminLogUpdateData",
    "AdminLogListData",
]