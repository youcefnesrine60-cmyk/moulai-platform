# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / CALLBACK ROUTER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for callback router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import re
from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

CallbackHandler = Callable[..., Awaitable[Any]]

# ==============================================
# 📌 CALLBACK ROUTER
# ==============================================


class CallbackRouter:

    # ==========================================
    # 🚀 INIT
    # ==========================================

    def __init__(
        self,
    ) -> None:

        self.routes: list[
            tuple[
                re.Pattern[str],
                CallbackHandler,
            ]
        ] = []

    # ==========================================
    # ➕ REGISTER ROUTE
    # ==========================================

    def register(
        self,
        *,
        pattern: str,
        handler: CallbackHandler,
    ) -> None:

        self.routes.append(
            (
                re.compile(pattern),
                handler,
            )
        )

    # ==========================================
    # 📌 DISPATCH CALLBACK
    # ==========================================

    async def dispatch(
        self,
        *,
        callback_data: str,
        chat_id: int,
        message_id: int,
    ) -> Any:
        """
        توزيع الكولباك إلى المعالج المناسب

        Args:
            callback_data: بيانات الكولباك من Telegram
            chat_id: معرف المستخدم
            message_id: معرف الرسالة
        """
        # ======================================
        # 🔍 SEARCH MATCHING ROUTE
        # ======================================

        for regex, handler in self.routes:

            match = regex.match(callback_data)

            if not match:
                continue

            logger.info(
                "callback_route_matched",
                extra={
                    "callback_data": callback_data,
                    "handler": handler.__name__,
                },
            )

            # ✅ تمرير المعاملات بشكل صحيح (جميعها مسماه)
            return await handler(
                chat_id=chat_id,
                message_id=message_id,
                callback_data=callback_data,
                match=match,
            )

        # ======================================
        # 🚫 NO ROUTE FOUND
        # ======================================

        logger.warning(
            "callback_route_not_found",
            extra={
                "callback_data": callback_data,
            },
        )

        return None
