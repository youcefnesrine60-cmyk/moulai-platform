# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🔍 RESTAURANT VALIDATORS
# دوال التحقق من صحة بيانات المطاعم
# ==============================================

"""MoulAI operational module for validators.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Dict, Any

from app.core.exceptions import ValidationError

# ==============================================
# 🧩 CONSTANTS
# ==============================================

MAX_RESTAURANTS_PER_OWNER = 5
VALID_RESTAURANT_TYPES = {"restaurant", "cafe", "fast_food", "bakery", "pizza", "other"}


# ==============================================
# 🔍 VALIDATION FUNCTIONS
# ==============================================

# ==============================================
# VALIDATE RESTAURANT TYPE
# ==============================================


def validate_restaurant_type(
    restaurant_type: str,
) -> str:
    """
    التحقق من صحة نوع المطعم.

    Args:
        restaurant_type: نوع المطعم

    Returns:
        str: نوع المطعم المدقق

    Raises:
        ValidationError: إذا كان النوع غير صالح
    """
    if restaurant_type not in VALID_RESTAURANT_TYPES:
        raise ValidationError(
            message=f"نوع المطعم '{restaurant_type}' غير صالح",
            details={
                "type": restaurant_type,
                "valid_types": list(VALID_RESTAURANT_TYPES),
            },
        )
    return restaurant_type


# ==============================================
# VALIDATE OWNER LIMIT
# ==============================================


def validate_owner_limit(
    current_count: int,
) -> None:
    """
    التحقق من عدم تجاوز المالك للحد الأقصى للمطاعم.

    Args:
        current_count: عدد المطاعم الحالية

    Raises:
        ValidationError: إذا تجاوز المالك الحد الأقصى
    """
    if current_count >= MAX_RESTAURANTS_PER_OWNER:
        raise ValidationError(
            message=f"تجاوزت الحد الأقصى للمطاعم ({MAX_RESTAURANTS_PER_OWNER})",
            details={
                "current_count": current_count,
                "max_allowed": MAX_RESTAURANTS_PER_OWNER,
            },
        )


# ==============================================
# VALIDATE METRICS VALUES
# ==============================================


def validate_metrics_values(
    updates: Dict[str, Any],
) -> None:
    """
    التحقق من صحة قيم المقاييس.

    Args:
        updates: قاموس القيم المراد تحديثها

    Raises:
        ValidationError: إذا كانت أي قيمة غير صالحة
    """
    if "products_count" in updates and updates["products_count"] < 0:
        raise ValidationError(
            message="عدد المنتجات لا يمكن أن يكون سالباً",
        )

    if "categories_count" in updates and updates["categories_count"] < 0:
        raise ValidationError(
            message="عدد التصنيفات لا يمكن أن يكون سالباً",
        )

    if "monthly_orders" in updates and updates["monthly_orders"] < 0:
        raise ValidationError(
            message="عدد الطلبات الشهرية لا يمكن أن يكون سالباً",
        )

    if "average_order_value" in updates and updates["average_order_value"] < 0:
        raise ValidationError(
            message="متوسط قيمة الطلب لا يمكن أن يكون سالباً",
        )


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "MAX_RESTAURANTS_PER_OWNER",
    "VALID_RESTAURANT_TYPES",
    "validate_restaurant_type",
    "validate_owner_limit",
    "validate_metrics_values",
]
