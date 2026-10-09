# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / TELEGRAM / BASE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for base.

Part of MoulAI Platform - Agent-as-a-Service.
"""

import asyncio
import httpx

from app.services.telegram.client import client
from app.core.logger import logger
from app.services.telegram.constants import BASE_URL, MAX_RETRIES

# ============================================
# 🧩 TYPES
# ============================================

TelegramResponse = dict | None

# ============================================
# 📡 BASE REQUEST
# ============================================


async def _post(*, method: str, data: dict) -> TelegramResponse:

    # ========================================
    # 🔁 RETRY LOOP
    # ========================================

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug(
                "telegram_request_started", extra={"method": method, "attempt": attempt}
            )

            response = await client.post(f"{BASE_URL}/{method}", json=data)

            # ==================================
            # 📦 JSON RESPONSE
            # ==================================

            result = response.json()

            # ==================================
            # 🚫 HTTP ERROR
            # ==================================

            if response.status_code >= 400:
                logger.error(
                    "telegram_http_error",
                    extra={
                        "method": method,
                        "status_code": response.status_code,
                        "response": result,
                    },
                )
                return result

            # ==================================
            # 🚫 TELEGRAM API ERROR
            # ==================================

            if not result.get("ok"):
                logger.error(
                    "telegram_api_error", extra={"method": method, "response": result}
                )
                return result

            # ==================================
            # ✅ SUCCESS
            # ==================================

            logger.info("telegram_api_success", extra={"method": method})
            return result

        # ======================================
        # 🚫 REQUEST ERROR
        # ======================================

        except httpx.RequestError as e:
            logger.warning(
                "telegram_request_retry",
                extra={"method": method, "attempt": attempt, "error": str(e)},
            )

            # ==============================
            # 🔁 RETRY
            # ==============================

            if attempt < MAX_RETRIES:
                logger.info(
                    "telegram_request_retrying",
                    extra={"method": method, "attempt": attempt},
                )
                await asyncio.sleep(1)
                continue

            logger.exception(
                "telegram_request_failed", extra={"method": method, "error": str(e)}
            )
            return None

        # ======================================
        # 🚫 INVALID JSON
        # ======================================

        except ValueError as e:
            logger.exception(
                "telegram_invalid_json", extra={"method": method, "error": str(e)}
            )
            return None

        # ======================================
        # 🚫 UNKNOWN ERROR
        # ======================================

        except Exception as e:

            logger.exception(
                "telegram_unknown_error", extra={"method": method, "error": str(e)}
            )
            return None
    return None
