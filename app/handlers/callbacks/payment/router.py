# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / PAYMENT / ROUTER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router

# ==============================================
# 📥 استيراد معالجات الدفع
# ==============================================

# 📡 معالجات بوابات الدفع الخارجية (Webhook)
from app.handlers.callbacks.payment.payment_callback import (
    handle_payment_success as handle_external_success,
    handle_payment_failure as handle_external_failure,
)

# 💬 معالجات تفاعلات المستخدم داخل Telegram
from app.handlers.callbacks.payment.payment_handlers import (
    handle_payment_success as handle_telegram_success,
    handle_payment_failure as handle_telegram_failure,
)

# ==============================================
# 🚀 REGISTER PAYMENT ROUTES
# ==============================================


async def register_payment_routes() -> None:
    """
    تسجيل جميع مسارات الدفع في الـ Router

    المسارات تنقسم إلى نوعين:
    1. مسارات خارجية (Webhook) - من بوابات الدفع
    2. مسارات داخلية (Telegram) - من تفاعلات المستخدم
    """
    logger.info(
        "registering_payment_routes",
    )

    # ==========================================
    # 📡 EXTERNAL PAYMENT CALLBACKS
    # معالجة ردود بوابات الدفع الخارجية
    # (Stripe, PayPal, CCP, BaridiMob)
    # ==========================================

    # 💳 نجاح الدفع من بوابة خارجية
    # مثال: payment_success_tx_123456
    router.register(
        pattern=r"^payment_success_(?P<external_reference>.+)$",
        handler=handle_external_success,
    )

    # ❌ فشل الدفع من بوابة خارجية
    # مثال: payment_failure_tx_123456
    router.register(
        pattern=r"^payment_failure_(?P<external_reference>.+)$",
        handler=handle_external_failure,
    )

    # ==========================================
    # 💬 TELEGRAM PAYMENT CALLBACKS
    # معالجة تفاعلات المستخدم داخل Telegram
    # ==========================================

    # ✅ تأكيد الدفع من داخل Telegram
    # مثال: payment_confirm_15 (حيث 15 هو order_id)
    router.register(
        pattern=r"^payment_confirm_(\d+)$",
        handler=handle_telegram_success,
    )

    # 🔄 إعادة محاولة الدفع
    # مثال: retry_payment_15 (حيث 15 هو order_id)
    router.register(
        pattern=r"^retry_payment_(\d+)$",
        handler=handle_telegram_failure,
    )

    # 🔙 رجوع إلى واجهة الدفع
    # مثال: back_to_payment_15 (حيث 15 هو order_id)
    router.register(
        pattern=r"^back_to_payment_(\d+)$",
        handler=handle_telegram_failure,
    )

    # ==========================================
    # 💳 طرق الدفع داخل Telegram
    # اختيار طريقة الدفع من قبل المستخدم
    # ==========================================

    # 💰 دفع نقداً (Cash) - الطريقة الافتراضية
    # مثال: payment_cash_15
    router.register(
        pattern=r"^payment_cash_(\d+)$",
        handler=handle_telegram_success,
    )

    # 💳 دفع ببطاقة POS (Card)
    # مثال: payment_card_15
    router.register(
        pattern=r"^payment_card_(\d+)$",
        handler=handle_telegram_success,
    )

    # 📱 دفع عبر CCP (إذا فعّله المطعم)
    # مثال: payment_ccp_15
    router.register(
        pattern=r"^payment_ccp_(\d+)$",
        handler=handle_telegram_success,
    )

    # 📱 دفع عبر بريدي موب (إذا فعّله المطعم)
    # مثال: payment_baridimob_15
    router.register(
        pattern=r"^payment_baridimob_(\d+)$",
        handler=handle_telegram_success,
    )

    # 🌐 دفع عبر Stripe (إذا فعّله المطعم)
    # مثال: payment_stripe_15
    router.register(
        pattern=r"^payment_stripe_(\d+)$",
        handler=handle_telegram_success,
    )

    # 🌐 دفع عبر PayPal (إذا فعّله المطعم)
    # مثال: payment_paypal_15
    router.register(
        pattern=r"^payment_paypal_(\d+)$",
        handler=handle_telegram_success,
    )

    logger.info(
        "payment_routes_registered",
    )
