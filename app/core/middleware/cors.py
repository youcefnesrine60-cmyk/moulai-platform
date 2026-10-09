# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / CORE / MIDDLEWARE / CORS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for cors.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger

# ==============================================
# 🧩 TYPES
# ==============================================

OriginsList = List[str]

# ==============================================
# 🚀 SETUP CORS
# ==============================================


def setup_cors(
    app: FastAPI,
) -> None:
    """
    إعداد CORS للتطبيق

    يسمح للواجهة الأمامية (Frontend) بالاتصال بالـ API

    Args:
        app: تطبيق FastAPI
    """
    # تحويل النطاقات من نص إلى قائمة
    origins_raw: str = settings.ALLOWED_ORIGINS
    origins: OriginsList = [
        origin.strip() for origin in origins_raw.split(",") if origin.strip()
    ]

    logger.info(
        "cors_configured",
        extra={
            "allowed_origins": origins,
            "environment": settings.ENVIRONMENT,
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # ✅ النطاقات المسموح بها
        allow_credentials=True,  # ✅ السماح بإرسال الكوكيز
        allow_methods=["*"],  # ✅ يسمح بكل الطرق (GET, POST, PUT, DELETE)
        allow_headers=["*"],  # ✅ يسمح بكل الرؤوس
    )
