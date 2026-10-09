# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / HANDLERS / CALLBACKS / OWNER / ROUTER
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for router.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.core.logger import logger
from app.core.router_instance import router
from app.handlers.callbacks.owner.confirm import confirm_callback
from app.handlers.callbacks.owner.register import (
    owner_callback,
    consent_callback,
)
from app.handlers.callbacks.owner.navigation import (
    back_main_callback,
    back_step_callback,
    decline_callback,
)

# =================================================
# 🚀 REGISTER OWNER ROUTES
# =================================================


async def register_owner_routes() -> None:

    # ==========================================
    # 👤 OWNER ROUTES
    # ==========================================

    router.register(
        pattern=r"^owner$",
        handler=owner_callback,
    )

    # ==========================================
    # ✅ CONSENT & CONFIRMATION
    # ==========================================

    router.register(
        pattern=r"^consent_.*$",
        handler=consent_callback,
    )

    router.register(
        pattern=r"^confirm$",
        handler=confirm_callback,
    )

    # ==========================================
    # 🔙 NAVIGATION
    # ==========================================

    router.register(
        pattern=r"^back_main$",
        handler=back_main_callback,
    )

    router.register(
        pattern=r"^back_step$",
        handler=back_step_callback,
    )

    router.register(
        pattern=r"^decline$",
        handler=decline_callback,
    )

    logger.info(
        "owner_callback_routes_registered",
    )
