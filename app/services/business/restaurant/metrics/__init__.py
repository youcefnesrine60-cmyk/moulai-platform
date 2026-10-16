# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS SERVICES - PACKAGE INIT
# ==============================================

"""Package initializer and public module exports.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.services.business.restaurant.metrics.service import (
    RestaurantMetricsService,
    MetricsDict,
)
from app.services.business.restaurant.metrics.handlers import MetricsEventHandlers

# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantMetricsService",
    "MetricsDict",
    "MetricsEventHandlers",
]
