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
from app.handlers.callbacks.customer.payment import (
    back_to_payment_callback,
    payment_confirm_callback,
    payment_method_callback,
    retry_payment_callback,
)


async def register_payment_routes() -> None:
    """Register customer payment navigation; gateway events arrive over HTTP."""
    router.register(
        pattern=r"^payment_(?:cash|card|ccp|baridimob|stripe|paypal)_(\d+)$",
        handler=payment_method_callback,
    )
    router.register(
        pattern=r"^payment_confirm_(\d+)$", handler=payment_confirm_callback
    )
    router.register(pattern=r"^retry_payment_(\d+)$", handler=retry_payment_callback)
    router.register(
        pattern=r"^back_to_payment_(\d+)$", handler=back_to_payment_callback
    )
    logger.info("payment_routes_registered")
