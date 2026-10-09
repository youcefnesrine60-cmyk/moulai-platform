# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / ORDERS / CONSTANTS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for constants.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Set, Dict

# ==============================================
# 🧩 FEATURE ID
# ==============================================

# معرف ميزة الطلبات في نظام الميزات
ORDERS_FEATURE_ID: int = 6

# ==============================================
# 🔒 LOCKED STATUSES
# ==============================================

# الحالات التي تمنع تعديل الطلب (Lock Order)
# عندما يكون الطلب في هذه الحالات، لا يمكن تعديله أو إلغاؤه
LOCKED_STATUSES: Set[str] = {
    "delivering",  # قيد التوصيل
    "delivered",  # تم التوصيل
    "completed",  # مكتمل
    "cancelled",  # ملغى
}

# ==============================================
# 🟢 ALLOWED TRANSITIONS
# ==============================================

# الانتقالات المسموحة بين الحالات
# المفتاح: الحالة الحالية، القيمة: قائمة الحالات المسموح الانتقال إليها
ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"delivering", "cancelled"},
    "delivering": {"delivered", "cancelled"},
    "delivered": {"completed"},
    "completed": set(),
    "cancelled": set(),
}

# ==============================================
# 📊 STATUS_DISPLAY_NAMES
# ==============================================

# الأسماء المعروضة لكل حالة (للواجهات)
STATUS_DISPLAY_NAMES: Dict[str, str] = {
    "pending": "⏳ قيد الانتظار",
    "confirmed": "✅ مؤكد",
    "preparing": "👨‍🍳 قيد التحضير",
    "ready": "🍽️ جاهز",
    "delivering": "🚚 قيد التوصيل",
    "delivered": "📦 تم التوصيل",
    "completed": "✅ مكتمل",
    "cancelled": "❌ ملغى",
}

# ==============================================
# 🎨 STATUS_COLORS
# ==============================================

# الألوان لكل حالة (للواجهات)
STATUS_COLORS: Dict[str, str] = {
    "pending": "#FFA500",  # برتقالي
    "confirmed": "#2196F3",  # أزرق
    "preparing": "#FF9800",  # برتقالي غامق
    "ready": "#4CAF50",  # أخضر
    "delivering": "#9C27B0",  # بنفسجي
    "delivered": "#00BCD4",  # فيروزي
    "completed": "#8BC34A",  # أخضر فاتح
    "cancelled": "#F44336",  # أحمر
}

# ==============================================
# 🔄 STATUS_ORDER
# ==============================================

# ترتيب الحالات (للعرض في التقارير)
STATUS_ORDER: Dict[str, int] = {
    "pending": 1,
    "confirmed": 2,
    "preparing": 3,
    "ready": 4,
    "delivering": 5,
    "delivered": 6,
    "completed": 7,
    "cancelled": 8,
}

# ==============================================
# 📋 STATUS_DESCRIPTIONS
# ==============================================

# وصف لكل حالة
STATUS_DESCRIPTIONS: Dict[str, str] = {
    "pending": "تم استلام الطلب في انتظار التأكيد",
    "confirmed": "تم تأكيد الطلب من قبل المطعم",
    "preparing": "الطلب قيد التحضير في المطبخ",
    "ready": "الطلب جاهز للتسليم أو التوصيل",
    "delivering": "الطلب في طريقه إلى العميل",
    "delivered": "تم توصيل الطلب إلى العميل",
    "completed": "اكتمل الطلب بنجاح",
    "cancelled": "تم إلغاء الطلب",
}

# ==============================================
# ✅ COMPLETABLE STATUSES
# ==============================================

# الحالات التي يمكن إكمالها
COMPLETABLE_STATUSES: Set[str] = {
    "delivering",
    "delivered",
    "ready",
    "confirmed",
}

# ==============================================
# ❌ CANCELLABLE STATUSES
# ==============================================

# الحالات التي يمكن إلغاؤها
CANCELLABLE_STATUSES: Set[str] = {
    "pending",
    "confirmed",
    "preparing",
    "ready",
    "delivering",
}

# ==============================================
# 🔄 EDITABLE STATUSES
# ==============================================

# الحالات التي يمكن تعديلها (إضافة/حذف عناصر)
EDITABLE_STATUSES: Set[str] = {
    "pending",
    "confirmed",
}

# ==============================================
# 📊 PAYMENT_REQUIRED_STATUSES
# ==============================================

# الحالات التي تتطلب الدفع
PAYMENT_REQUIRED_STATUSES: Set[str] = {
    "confirmed",
    "preparing",
    "ready",
    "delivering",
    "delivered",
    "completed",
}

# ==============================================
# 📋 ALL_STATUSES
# ==============================================

# قائمة بجميع الحالات الممكنة
ALL_STATUSES: Set[str] = {
    "pending",
    "confirmed",
    "preparing",
    "ready",
    "delivering",
    "delivered",
    "completed",
    "cancelled",
}

# ==============================================
# 🎯 VALID_STATUSES
# ==============================================

# الحالات الصالحة (للتحقق من صحة المدخلات)
VALID_STATUSES: Set[str] = ALL_STATUSES

# ==============================================
# 🧩 TYPE ALIASES
# ==============================================

StatusType = str
StatusSet = Set[str]
StatusDict = Dict[str, str]
StatusTransitionDict = Dict[str, Set[str]]
StatusOrderDict = Dict[str, int]


# ==============================================
# 🔧 HELPER FUNCTIONS
# ==============================================


def get_status_display_name(status: str) -> str:
    """
    الحصول على الاسم المعروض للحالة.

    Args:
        status: الحالة

    Returns:
        str: الاسم المعروض
    """
    return STATUS_DISPLAY_NAMES.get(status, status)


# ==============================================
# GET STATUS COLOR
# ==============================================


def get_status_color(status: str) -> str:
    """
    الحصول على لون الحالة.

    Args:
        status: الحالة

    Returns:
        str: لون الحالة
    """
    return STATUS_COLORS.get(status, "#808080")  # رمادي افتراضي


# ==============================================
# GET STATUS DESCRIPTION
# ==============================================


def get_status_description(status: str) -> str:
    """
    الحصول على وصف الحالة.

    Args:
        status: الحالة

    Returns:
        str: وصف الحالة
    """
    return STATUS_DESCRIPTIONS.get(status, "حالة غير معروفة")


# ==============================================
# IS VALID STATUS
# ==============================================


def is_valid_status(status: str) -> bool:
    """
    التحقق من صحة الحالة.

    Args:
        status: الحالة

    Returns:
        bool: True إذا كانت الحالة صالحة
    """
    return status in VALID_STATUSES


# ==============================================
# IS LOCKED STATUS
# ==============================================


def is_locked_status(status: str) -> bool:
    """
    التحقق من أن الحالة مقفلة (لا يمكن تعديلها).

    Args:
        status: الحالة

    Returns:
        bool: True إذا كانت الحالة مقفلة
    """
    return status in LOCKED_STATUSES


# ==============================================
# IS COMPLETABLE STATUS
# ==============================================


def is_completable_status(status: str) -> bool:
    """
    التحقق من أن الحالة قابلة للإكمال.

    Args:
        status: الحالة

    Returns:
        bool: True إذا كانت الحالة قابلة للإكمال
    """
    return status in COMPLETABLE_STATUSES


# ==============================================
# IS CANCELLABLE STATUS
# ==============================================


def is_cancellable_status(status: str) -> bool:
    """
    التحقق من أن الحالة قابلة للإلغاء.

    Args:
        status: الحالة

    Returns:
        bool: True إذا كانت الحالة قابلة للإلغاء
    """
    return status in CANCELLABLE_STATUSES


# ==============================================
# IS EDITABLE STATUS
# ==============================================


def is_editable_status(status: str) -> bool:
    """
    التحقق من أن الحالة قابلة للتعديل.

    Args:
        status: الحالة

    Returns:
        bool: True إذا كانت الحالة قابلة للتعديل
    """
    return status in EDITABLE_STATUSES


# ==============================================
# GET ALLOWED TRANSITIONS
# ==============================================


def get_allowed_transitions(status: str) -> Set[str]:
    """
    الحصول على الحالات المسموح الانتقال إليها من حالة معينة.

    Args:
        status: الحالة الحالية

    Returns:
        Set[str]: مجموعة الحالات المسموح الانتقال إليها
    """
    return ALLOWED_TRANSITIONS.get(status, set())


# ==============================================
# CAN TRANSITION
# ==============================================


def can_transition(from_status: str, to_status: str) -> bool:
    """
    التحقق من إمكانية الانتقال من حالة إلى أخرى.

    Args:
        from_status: الحالة الحالية
        to_status: الحالة المطلوبة

    Returns:
        bool: True إذا كان الانتقال مسموحاً
    """
    return to_status in get_allowed_transitions(from_status)


# ==============================================
# GET NEXT STATUSES
# ==============================================


def get_next_statuses(status: str) -> Set[str]:
    """
    الحصول على الحالات التالية المسموح بها من حالة معينة.

    Args:
        status: الحالة الحالية

    Returns:
        Set[str]: مجموعة الحالات التالية
    """
    return get_allowed_transitions(status)


# ==============================================
# GET PREVIOUS STATUSES
# ==============================================


def get_previous_statuses(status: str) -> Set[str]:
    """
    الحصول على الحالات السابقة التي يمكن الانتقال منها إلى حالة معينة.

    Args:
        status: الحالة المطلوبة

    Returns:
        Set[str]: مجموعة الحالات السابقة
    """
    previous = set()
    for from_status, to_statuses in ALLOWED_TRANSITIONS.items():
        if status in to_statuses:
            previous.add(from_status)
    return previous


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Constants
    "ORDERS_FEATURE_ID",
    "LOCKED_STATUSES",
    "ALLOWED_TRANSITIONS",
    "STATUS_DISPLAY_NAMES",
    "STATUS_COLORS",
    "STATUS_ORDER",
    "STATUS_DESCRIPTIONS",
    "COMPLETABLE_STATUSES",
    "CANCELLABLE_STATUSES",
    "EDITABLE_STATUSES",
    "PAYMENT_REQUIRED_STATUSES",
    "ALL_STATUSES",
    "VALID_STATUSES",
    # Type Aliases
    "StatusType",
    "StatusSet",
    "StatusDict",
    "StatusTransitionDict",
    "StatusOrderDict",
    # Helper Functions
    "get_status_display_name",
    "get_status_color",
    "get_status_description",
    "is_valid_status",
    "is_locked_status",
    "is_completable_status",
    "is_cancellable_status",
    "is_editable_status",
    "get_allowed_transitions",
    "can_transition",
    "get_next_statuses",
    "get_previous_statuses",
]
