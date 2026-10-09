# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACK ROUTES
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for callback routes.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router

# ==============================================
# 📥 استيراد جميع المسارات من المجلدات المختلفة
# ==============================================

# 🛒 مسارات الزبون (بما فيها مسارات السلة)
from app.handlers.callbacks.customer import (
    register_customer_routes,
    register_cart_routes,
)

# 👨‍🍳 مسارات المالك ولوحة التحكم
from app.handlers.callbacks.owner import (
    register_owner_routes,
    register_owner_dashboard_routes,
)

# 💳 مسارات الدفع
from app.handlers.callbacks.payment import register_payment_routes

# 🍽️ مسارات المطعم
from app.handlers.callbacks.restaurant import register_restaurant_routes

# 📦 مسارات الطلبات
from app.handlers.callbacks.order import register_order_routes

# 📌 مسارات عامة (Fallback)
from app.handlers.callbacks.order_callbacks import order_callback
from app.handlers.callbacks.type_callbacks import type_callback

# 🛡️ مسارات المسؤول
from app.handlers.callbacks.admin.admin_handlers import (
    admin_dashboard_callback,
    admin_requests_callback,
    admin_request_details_callback,
    admin_approve_callback,
    admin_reject_callback,
)

# ==============================================
# 🚀 SETUP ROUTES
# ==============================================


async def setup_routes() -> None:
    """
    تسجيل جميع مسارات الكولباك في النظام

    يتم استدعاء هذه الدالة عند بدء تشغيل التطبيق
    لتسجيل جميع المسارات في الـ Router المركزي.
    """
    logger.info(
        "registering_callback_routes",
    )

    # ==========================================
    # 👨‍🍳 OWNER ROUTES
    # مسارات المالك (تسجيل، موافقة، تنقل)
    # ==========================================

    await register_owner_routes()

    # ==========================================
    # 👤 CUSTOMER ROUTES
    # مسارات الزبون (اختيار مطعم، عرض منتجات)
    # ==========================================

    await register_customer_routes()

    # ==========================================
    # 🛒 CART ROUTES
    # مسارات السلة (إضافة، حذف، تعديل الكميات)
    # ==========================================

    await register_cart_routes()

    # ==========================================
    # 💳 PAYMENT ROUTES
    # مسارات الدفع (اختيار طريقة، تأكيد، إعادة محاولة)
    # ==========================================

    await register_payment_routes()

    # ==========================================
    # 🏪 OWNER DASHBOARD ROUTES
    # مسارات لوحة تحكم المالك (إدارة الطلبات، المنتجات)
    # ==========================================

    await register_owner_dashboard_routes()

    # ==========================================
    # 🍽️ RESTAURANT ROUTES
    # مسارات المطعم (تفاصيل، قائمة)
    # ==========================================

    await register_restaurant_routes()

    # ==========================================
    # 📦 ORDER ROUTES
    # مسارات الطلبات (تفاصيل، تتبع)
    # ==========================================

    await register_order_routes()

    # ==========================================
    # 🏷️ TYPE ROUTES
    # مسارات اختيار نوع المطعم
    # ==========================================

    router.register(
        pattern=r"^type_.*",
        handler=type_callback,
    )

    # ==========================================
    # 📦 BUSINESS ROUTES (Fallback)
    # مسارات عامة لالتقاط أي كولباك غير معالج
    # ==========================================

    # 📦 طلب محدد (order_15)
    router.register(
        pattern=r"^order_(\d+)$",
        handler=order_callback,
    )

    # 🍔 منتج محدد (product_15)
    router.register(
        pattern=r"^product_(\d+)$",
        handler=order_callback,
    )

    # 💳 دفع محدد (payment_xxx)
    router.register(
        pattern=r"^payment_.*",
        handler=order_callback,
    )

    # 🎫 قسيمة (coupon_xxx)
    router.register(
        pattern=r"^coupon_.*",
        handler=order_callback,
    )

    # 🔙 رجوع إلى السلة (back_to_cart_15)
    router.register(
        pattern=r"^back_to_cart_(\d+)$",
        handler=order_callback,
    )

    # 🔙 رجوع إلى الدفع (back_to_payment_15)
    router.register(
        pattern=r"^back_to_payment_(\d+)$",
        handler=order_callback,
    )

    # 🔄 إعادة محاولة الدفع (retry_payment_15)
    router.register(
        pattern=r"^retry_payment_(\d+)$",
        handler=order_callback,
    )

    # 📦 تتبع الطلب (track_order_15)
    router.register(
        pattern=r"^track_order_(\d+)$",
        handler=order_callback,
    )

    # ==========================================
    # 🛡️ ADMIN ROUTES
    # مسارات المسؤول (لوحة التحكم، الموافقة، الرفض)
    # ==========================================

    # 🛡️ عرض لوحة تحكم المسؤول
    router.register(
        pattern=r"^admin_dashboard$",
        handler=admin_dashboard_callback,
    )

    # 📋 عرض طلبات التسجيل المعلقة
    router.register(
        pattern=r"^admin_requests$",
        handler=admin_requests_callback,
    )

    # 📋 عرض تفاصيل طلب تسجيل محدد
    router.register(
        pattern=r"^admin_request_(\d+)$",
        handler=admin_request_details_callback,
    )

    # ✅ الموافقة على طلب تسجيل
    router.register(
        pattern=r"^admin_approve_(\d+)$",
        handler=admin_approve_callback,
    )

    # ❌ رفض طلب تسجيل
    router.register(
        pattern=r"^admin_reject_(\d+)$",
        handler=admin_reject_callback,
    )

    # ==========================================
    # ✅ LOGGING
    # تسجيل اكتمال تسجيل المسارات
    # ==========================================

    logger.info(
        "callback_routes_registered",
    )
