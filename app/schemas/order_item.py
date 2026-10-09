# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 ORDER ITEM SCHEMAS
# نماذج Pydantic لتفاصيل الطلب
# تدير التحقق من صحة البيانات وتسلسلها لتفاصيل الطلب
# ==============================================

"""MoulAI operational module for order item.

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

OrderItemData = Dict[str, Any]
OrderItemUpdateData = Dict[str, Any]
OrderItemListData = List[Dict[str, Any]]


# ==============================================
# 📦 ORDER ITEM SCHEMAS
# ==============================================

# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class OrderItemBase(BaseModel):
    """
    المخطط الأساسي لتفاصيل الطلب.

    Attributes:
        order_id: معرف الطلب
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية
        total_price: السعر الإجمالي
    """

    order_id: int = Field(
        ...,
        description="معرف الطلب",
        json_schema_extra={"example": 1},
    )
    product_id: int = Field(
        ...,
        description="معرف المنتج",
        json_schema_extra={"example": 1},
    )
    product_name: str = Field(
        ...,
        max_length=255,
        description="اسم المنتج",
        json_schema_extra={"example": "بيتزا مارغريتا"},
    )
    unit_price: float = Field(
        ...,
        ge=0,
        description="سعر الوحدة",
        json_schema_extra={"example": 1500.00},
    )
    quantity: int = Field(
        ...,
        ge=1,
        description="الكمية",
        json_schema_extra={"example": 2},
    )
    total_price: float = Field(
        ...,
        ge=0,
        description="السعر الإجمالي",
        json_schema_extra={"example": 3000.00},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class OrderItemCreate(BaseModel):
    """
    مخطط إنشاء تفاصيل طلب جديدة.

    Attributes:
        order_id: معرف الطلب
        product_id: معرف المنتج
        product_name: اسم المنتج
        unit_price: سعر الوحدة
        quantity: الكمية
        total_price: السعر الإجمالي
        options: خيارات المنتج (اختياري)
    """

    order_id: int = Field(
        ...,
        description="معرف الطلب",
        json_schema_extra={"example": 1},
    )
    product_id: int = Field(
        ...,
        description="معرف المنتج",
        json_schema_extra={"example": 1},
    )
    product_name: str = Field(
        ...,
        max_length=255,
        description="اسم المنتج",
        json_schema_extra={"example": "بيتزا مارغريتا"},
    )
    unit_price: float = Field(
        ...,
        ge=0,
        description="سعر الوحدة",
        json_schema_extra={"example": 1500.00},
    )
    quantity: int = Field(
        ...,
        ge=1,
        description="الكمية",
        json_schema_extra={"example": 2},
    )
    total_price: float = Field(
        ...,
        ge=0,
        description="السعر الإجمالي",
        json_schema_extra={"example": 3000.00},
    )
    options: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="خيارات المنتج",
        json_schema_extra={
            "example": [
                {
                    "option_group_name": "حجم",
                    "option_name": "كبير",
                    "additional_price": 200,
                }
            ]
        },
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class OrderItemUpdate(BaseModel):
    """
    مخطط تحديث تفاصيل الطلب.

    Attributes:
        quantity: الكمية الجديدة
        total_price: السعر الإجمالي الجديد
    """

    quantity: Optional[int] = Field(
        None,
        ge=1,
        description="الكمية الجديدة",
        json_schema_extra={"example": 3},
    )
    total_price: Optional[float] = Field(
        None,
        ge=0,
        description="السعر الإجمالي الجديد",
        json_schema_extra={"example": 4500.00},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class OrderItemResponse(OrderItemBase):
    """
    مخطط استجابة تفاصيل الطلب.

    Attributes:
        id: معرف تفاصيل الطلب
        created_at: تاريخ الإنشاء
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف تفاصيل الطلب",
        json_schema_extra={"example": 1},
    )
    created_at: datetime = Field(
        ...,
        description="تاريخ الإنشاء",
    )


# ==============================================
# 🎯 ORDER ITEM WITH OPTIONS RESPONSE
# ==============================================


class OrderItemWithOptionsResponse(OrderItemResponse):
    """
    مخطط استجابة تفاصيل الطلب مع الخيارات.

    Attributes:
        options: قائمة خيارات المنتج
    """

    model_config = ConfigDict(from_attributes=True)

    options: List["OrderItemOptionResponse"] = Field(
        default_factory=list,
        description="خيارات المنتج",
    )


# ==============================================
# 📋 LIST RESPONSE
# ==============================================


class OrderItemListResponse(BaseModel):
    """
    مخطط استجابة قائمة تفاصيل الطلب.

    Attributes:
        items: قائمة تفاصيل الطلب
        total: العدد الإجمالي
        skip: عدد السجلات المتخطية
        limit: الحد الأقصى للسجلات
    """

    model_config = ConfigDict(from_attributes=True)

    items: List[OrderItemResponse] = Field(
        ...,
        description="قائمة تفاصيل الطلب",
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


class OrderItemSummary(BaseModel):
    """
    مخطط ملخص تفاصيل الطلب.

    Attributes:
        total_items: إجمالي عدد العناصر
        total_quantity: إجمالي الكمية
        subtotal: المجموع الفرعي
        total_options_price: إجمالي سعر الخيارات
        total_price: السعر الإجمالي
    """

    model_config = ConfigDict(from_attributes=True)

    total_items: int = Field(
        ...,
        description="إجمالي عدد العناصر",
        json_schema_extra={"example": 5},
        ge=0,
    )
    total_quantity: int = Field(
        ...,
        description="إجمالي الكمية",
        json_schema_extra={"example": 10},
        ge=0,
    )
    subtotal: float = Field(
        ...,
        description="المجموع الفرعي",
        json_schema_extra={"example": 15000.00},
        ge=0,
    )
    total_options_price: float = Field(
        ...,
        description="إجمالي سعر الخيارات",
        json_schema_extra={"example": 500.00},
        ge=0,
    )
    total_price: float = Field(
        ...,
        description="السعر الإجمالي",
        json_schema_extra={"example": 15500.00},
        ge=0,
    )


# ==============================================
# 🎯 ORDER ITEM OPTION SCHEMAS
# ==============================================

# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class OrderItemOptionBase(BaseModel):
    """
    المخطط الأساسي لخيارات تفاصيل الطلب.

    Attributes:
        order_item_id: معرف تفاصيل الطلب
        option_group_name: اسم مجموعة الخيارات
        option_name: اسم الخيار
        additional_price: السعر الإضافي
    """

    order_item_id: int = Field(
        ...,
        description="معرف تفاصيل الطلب",
        json_schema_extra={"example": 1},
    )
    option_group_name: str = Field(
        ...,
        max_length=255,
        description="اسم مجموعة الخيارات",
        json_schema_extra={"example": "حجم"},
    )
    option_name: str = Field(
        ...,
        max_length=255,
        description="اسم الخيار",
        json_schema_extra={"example": "كبير"},
    )
    additional_price: float = Field(
        ...,
        ge=0,
        description="السعر الإضافي",
        json_schema_extra={"example": 200.00},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class OrderItemOptionCreate(BaseModel):
    """
    مخطط إنشاء خيار جديد لتفاصيل الطلب.

    Attributes:
        order_item_id: معرف تفاصيل الطلب
        option_group_name: اسم مجموعة الخيارات
        option_name: اسم الخيار
        additional_price: السعر الإضافي
    """

    order_item_id: int = Field(
        ...,
        description="معرف تفاصيل الطلب",
        json_schema_extra={"example": 1},
    )
    option_group_name: str = Field(
        ...,
        max_length=255,
        description="اسم مجموعة الخيارات",
        json_schema_extra={"example": "حجم"},
    )
    option_name: str = Field(
        ...,
        max_length=255,
        description="اسم الخيار",
        json_schema_extra={"example": "كبير"},
    )
    additional_price: float = Field(
        ...,
        ge=0,
        description="السعر الإضافي",
        json_schema_extra={"example": 200.00},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class OrderItemOptionUpdate(BaseModel):
    """
    مخطط تحديث خيار تفاصيل الطلب.

    Attributes:
        option_group_name: اسم مجموعة الخيارات الجديد
        option_name: اسم الخيار الجديد
        additional_price: السعر الإضافي الجديد
    """

    option_group_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم مجموعة الخيارات الجديد",
        json_schema_extra={"example": "حجم"},
    )
    option_name: Optional[str] = Field(
        None,
        max_length=255,
        description="اسم الخيار الجديد",
        json_schema_extra={"example": "وسط"},
    )
    additional_price: Optional[float] = Field(
        None,
        ge=0,
        description="السعر الإضافي الجديد",
        json_schema_extra={"example": 150.00},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class OrderItemOptionResponse(OrderItemOptionBase):
    """
    مخطط استجابة خيارات تفاصيل الطلب.

    Attributes:
        id: معرف الخيار
        created_at: تاريخ الإنشاء
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الخيار",
        json_schema_extra={"example": 1},
    )
    created_at: datetime = Field(
        ...,
        description="تاريخ الإنشاء",
    )


# ==============================================
# 📊 SUMMARY
# ==============================================


class OrderItemOptionSummary(BaseModel):
    """
    مخطط ملخص خيارات تفاصيل الطلب.

    Attributes:
        total_options: إجمالي عدد الخيارات
        total_additional_price: إجمالي السعر الإضافي
        groups: توزيع الخيارات حسب المجموعة
    """

    model_config = ConfigDict(from_attributes=True)

    total_options: int = Field(
        ...,
        description="إجمالي عدد الخيارات",
        json_schema_extra={"example": 3},
        ge=0,
    )
    total_additional_price: float = Field(
        ...,
        description="إجمالي السعر الإضافي",
        json_schema_extra={"example": 500.00},
        ge=0,
    )
    groups: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="توزيع الخيارات حسب المجموعة",
        json_schema_extra={
            "example": {"حجم": ["كبير", "وسط"], "إضافات": ["جبن إضافي"]}
        },
    )


# ==============================================
# 💳 ORDER PAYMENT SCHEMAS
# ==============================================

# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class OrderPaymentBase(BaseModel):
    """
    المخطط الأساسي لمدفوعات الطلب.

    Attributes:
        order_id: معرف الطلب
        payment_method: طريقة الدفع
        payment_status: حالة الدفع
        amount: المبلغ
        transaction_reference: مرجع المعاملة
        paid_at: تاريخ الدفع
    """

    order_id: int = Field(
        ...,
        description="معرف الطلب",
        json_schema_extra={"example": 1},
    )
    payment_method: str = Field(
        ...,
        max_length=50,
        description="طريقة الدفع",
        json_schema_extra={"example": "cash"},
    )
    payment_status: str = Field(
        "pending",
        max_length=50,
        description="حالة الدفع",
        json_schema_extra={"example": "pending"},
    )
    amount: float = Field(
        ...,
        ge=0,
        description="المبلغ",
        json_schema_extra={"example": 15500.00},
    )
    transaction_reference: Optional[str] = Field(
        None,
        max_length=255,
        description="مرجع المعاملة",
        json_schema_extra={"example": "TXN-123456"},
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="تاريخ الدفع",
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class OrderPaymentCreate(BaseModel):
    """
    مخطط إنشاء دفعة جديدة للطلب.

    Attributes:
        order_id: معرف الطلب
        payment_method: طريقة الدفع
        amount: المبلغ
        transaction_reference: مرجع المعاملة (اختياري)
    """

    order_id: int = Field(
        ...,
        description="معرف الطلب",
        json_schema_extra={"example": 1},
    )
    payment_method: str = Field(
        ...,
        max_length=50,
        description="طريقة الدفع",
        json_schema_extra={"example": "cash"},
    )
    amount: float = Field(
        ...,
        ge=0,
        description="المبلغ",
        json_schema_extra={"example": 15500.00},
    )
    transaction_reference: Optional[str] = Field(
        None,
        max_length=255,
        description="مرجع المعاملة",
        json_schema_extra={"example": "TXN-123456"},
    )


# ==============================================
# 📤 UPDATE SCHEMA
# ==============================================


class OrderPaymentUpdate(BaseModel):
    """
    مخطط تحديث دفعة الطلب.

    Attributes:
        payment_status: حالة الدفع الجديدة
        transaction_reference: مرجع المعاملة الجديد
        paid_at: تاريخ الدفع الجديد
    """

    payment_status: Optional[str] = Field(
        None,
        max_length=50,
        description="حالة الدفع الجديدة",
        json_schema_extra={"example": "paid"},
    )
    transaction_reference: Optional[str] = Field(
        None,
        max_length=255,
        description="مرجع المعاملة الجديد",
        json_schema_extra={"example": "TXN-789012"},
    )
    paid_at: Optional[datetime] = Field(
        None,
        description="تاريخ الدفع الجديد",
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class OrderPaymentResponse(OrderPaymentBase):
    """
    مخطط استجابة مدفوعات الطلب.

    Attributes:
        id: معرف الدفعة
        created_at: تاريخ الإنشاء
        updated_at: تاريخ آخر تحديث
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف الدفعة",
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
# 📊 PAYMENT STATUS UPDATE
# ==============================================


class OrderPaymentStatusUpdate(BaseModel):
    """
    مخطط تحديث حالة الدفع.

    Attributes:
        payment_status: حالة الدفع الجديدة
    """

    payment_status: str = Field(
        ...,
        max_length=50,
        description="حالة الدفع الجديدة",
        json_schema_extra={"example": "paid"},
    )


# ==============================================
# 📜 ORDER STATUS HISTORY SCHEMAS
# ==============================================

# ==============================================
# 📦 BASE SCHEMA
# ==============================================


class OrderStatusHistoryBase(BaseModel):
    """
    المخطط الأساسي لتاريخ حالة الطلب.

    Attributes:
        order_id: معرف الطلب
        status: الحالة الجديدة
        employee_id: معرف الموظف
        note: ملاحظة
    """

    order_id: int = Field(
        ...,
        description="معرف الطلب",
        json_schema_extra={"example": 1},
    )
    status: str = Field(
        ...,
        max_length=50,
        description="الحالة الجديدة",
        json_schema_extra={"example": "confirmed"},
    )
    employee_id: Optional[int] = Field(
        None,
        description="معرف الموظف",
        json_schema_extra={"example": 1},
    )
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="ملاحظة",
        json_schema_extra={"example": "تم تأكيد الطلب من قبل الموظف"},
    )


# ==============================================
# 📥 CREATE SCHEMA
# ==============================================


class OrderStatusHistoryCreate(BaseModel):
    """
    مخطط إنشاء سجل تاريخ حالة الطلب.

    Attributes:
        order_id: معرف الطلب
        status: الحالة الجديدة
        employee_id: معرف الموظف (اختياري)
        note: ملاحظة (اختياري)
    """

    order_id: int = Field(
        ...,
        description="معرف الطلب",
        json_schema_extra={"example": 1},
    )
    status: str = Field(
        ...,
        max_length=50,
        description="الحالة الجديدة",
        json_schema_extra={"example": "confirmed"},
    )
    employee_id: Optional[int] = Field(
        None,
        description="معرف الموظف",
        json_schema_extra={"example": 1},
    )
    note: Optional[str] = Field(
        None,
        max_length=500,
        description="ملاحظة",
        json_schema_extra={"example": "تم تأكيد الطلب من قبل الموظف"},
    )


# ==============================================
# 📤 RESPONSE SCHEMA
# ==============================================


class OrderStatusHistoryResponse(OrderStatusHistoryBase):
    """
    مخطط استجابة تاريخ حالة الطلب.

    Attributes:
        id: معرف السجل
        created_at: تاريخ الإنشاء
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description="معرف السجل",
        json_schema_extra={"example": 1},
    )
    created_at: datetime = Field(
        ...,
        description="تاريخ الإنشاء",
    )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Order Item
    "OrderItemBase",
    "OrderItemCreate",
    "OrderItemUpdate",
    "OrderItemResponse",
    "OrderItemWithOptionsResponse",
    "OrderItemListResponse",
    "OrderItemSummary",
    "OrderItemData",
    "OrderItemUpdateData",
    "OrderItemListData",
    # Order Item Option
    "OrderItemOptionBase",
    "OrderItemOptionCreate",
    "OrderItemOptionUpdate",
    "OrderItemOptionResponse",
    "OrderItemOptionSummary",
    # Order Payment
    "OrderPaymentBase",
    "OrderPaymentCreate",
    "OrderPaymentUpdate",
    "OrderPaymentResponse",
    "OrderPaymentStatusUpdate",
    # Order Status History
    "OrderStatusHistoryBase",
    "OrderStatusHistoryCreate",
    "OrderStatusHistoryResponse",
]
