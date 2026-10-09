# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / API / WEBHOOK
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for webhook.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from fastapi import APIRouter
from fastapi import Request

from app.core.dispatcher import dispatch_update
from app.core.logger import logger
from app.core.middleware.gateway import GatewayMiddleware
from app.core.middleware.request_logger import RequestLogger
from app.core.security.risk_engine import RiskEngine
from app.handlers.callback_routes import setup_routes

# ==============================================
# 🧩 TYPES
# ==============================================

WebhookResponse = dict[str, bool]


# ==============================================
# 🚀 API ROUTER
# ==============================================

router = APIRouter()

# ==============================================
# 🚀 REGISTER CALLBACK ROUTES
# ==============================================


# ✅ تصحيح: استخدام await مع الدالة غير المتزامنة
# ==============================================
# REGISTER ROUTES
# ==============================================


async def register_routes() -> None:
    """تسجيل جميع مسارات الكولباك في النظام"""
    await setup_routes()


# ==============================================
# 🚀 WEBHOOK ENDPOINT
# ==============================================


@router.post("/webhook")
async def telegram_webhook(*, request: Request) -> WebhookResponse:

    # ==========================================
    # 📦 PARSE REQUEST
    # ==========================================

    try:
        data = await request.json()
    except Exception as e:
        logger.exception("invalid_webhook_payload", extra={"error": str(e)})
        return {"ok": False}

    # ==========================================
    # 🔍 DEFAULT VALUES
    # ==========================================

    chat_id: int | None = None
    update_type = "unknown"
    text: str | None = None

    # ==========================================
    # 💬 MESSAGE UPDATE
    # ==========================================

    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text")
        update_type = "message"

        logger.info(
            "received_message",
            extra={"chat_id": chat_id, "text_length": len(text) if text else 0},
        )

    # ==========================================
    # 🔘 CALLBACK UPDATE
    # ==========================================

    elif "callback_query" in data:
        callback = data["callback_query"]
        message = callback.get("message")

        if not message:
            logger.warning("callback_without_message")
            return {"ok": False}

        chat_id = message["chat"]["id"]
        update_type = "callback"

        logger.info("received_callback", extra={"chat_id": chat_id})

    # ==========================================
    # 🚫 INVALID UPDATE
    # ==========================================

    if chat_id is None:
        logger.warning("webhook_missing_chat_id", extra={"data": data})
        return {"ok": False}

    # ==========================================
    # 📜 REQUEST LOGGER
    # ==========================================

    await RequestLogger.log(chat_id=chat_id, update_type=update_type)

    # ==========================================
    # 🌍 GATEWAY CHECK
    # ==========================================

    allowed = await GatewayMiddleware.process(chat_id=chat_id)

    if not allowed:
        logger.warning("gateway_blocked", extra={"chat_id": chat_id})
        return {"ok": False}

    # ==========================================
    # 🛡️ RISK ANALYSIS
    # ==========================================

    safe = await RiskEngine.analyze(chat_id=chat_id, text=text)

    if not safe:
        logger.warning("risk_blocked", extra={"chat_id": chat_id})
        return {"ok": False}

    # ==========================================
    # 🚀 DISPATCH UPDATE
    # ==========================================

    try:
        await dispatch_update(data=data)
    except Exception as e:
        logger.exception(
            "dispatch_update_failed", extra={"chat_id": chat_id, "error": str(e)}
        )
        return {"ok": False}

    # ==========================================
    # ✅ SUCCESS
    # ==========================================

    logger.info(
        "webhook_processed", extra={"chat_id": chat_id, "update_type": update_type}
    )

    return {"ok": True}


# ==============================================
# 🚀 تسجيل المسارات عند بدء التشغيل
# ==============================================


# ✅ تصحيح: استدعاء الدالة غير المتزامنة بشكل صحيح
# ==============================================
# STARTUP ROUTES
# ==============================================


async def startup_routes() -> None:
    """تسجيل جميع المسارات عند بدء التطبيق"""
    await register_routes()
