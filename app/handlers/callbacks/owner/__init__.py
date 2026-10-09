# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# PACKAGE INITIALIZER - APP / HANDLERS / CALLBACKS / OWNER /   INIT
# Package initialization and public exports component.
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.handlers.callbacks.owner.router import register_owner_routes
from app.handlers.callbacks.owner.owner_dashboard_routes import (
    register_owner_dashboard_routes,
)

__all__ = [
    "register_owner_routes",
    "register_owner_dashboard_routes",
]
