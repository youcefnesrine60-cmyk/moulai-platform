# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📊 RESTAURANT METRICS SERVICES - PACKAGE INIT
# ==============================================

from app.services.business.restaurant.metrics.service import RestaurantMetricsService, MetricsDict
from app.services.business.restaurant.metrics.handlers import MetricsEventHandlers
from app.services.business.restaurant.metrics.compat import (
    initialize_metrics,
    product_created,
    product_deleted,
    category_created,
    category_deleted,
    order_registered,
    get_metrics,
    get_metrics_summary,
    reset_metrics,
)


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    "RestaurantMetricsService",
    "MetricsDict",
    "MetricsEventHandlers",
    "initialize_metrics",
    "product_created",
    "product_deleted",
    "category_created",
    "category_deleted",
    "order_registered",
    "get_metrics",
    "get_metrics_summary",
    "reset_metrics",
]