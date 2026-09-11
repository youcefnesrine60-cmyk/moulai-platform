# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🚀 MoulAI MAIN APPLICATION
# ==============================================

"""التطبيق الرئيسي لمنصة مولاي."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ==============================================
# 📦 IMPORT ROUTERS
# ==============================================

# Admin
from app.api.v1.admin import (
    admin_router,
    admin_log_router,
    admin_session_router,
)

# API v1 Routers
from app.api.v1.branches import router as branches_router
from app.api.v1.categories import router as categories_router
from app.api.v1.option_group import router as option_groups_router
from app.api.v1.order_item import router as order_items_router
from app.api.v1.orders import router as orders_router
from app.api.v1.owners import router as owners_router
from app.api.v1.payments import router as payments_router
from app.api.v1.product_option import router as product_options_router
from app.api.v1.products import router as products_router
from app.api.v1.registration_request import router as registration_requests_router
# Restaurant (جميع الروترات مجمعة في ملف واحد)
from app.api.v1.restaurant import router as restaurant_router
from app.api.v1.user import router as users_router
from app.api.webhook import router as webhook_router
from app.api.webhook import register_routes

from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logger import logger


# ==============================================
# 🚀 LIFESPAN MANAGER
# ==============================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    إدارة دورة حياة التطبيق.
    
    - بدء التشغيل: تهيئة قاعدة البيانات وتسجيل المسارات
    - الإغلاق: إغلاق اتصال قاعدة البيانات
    
    Yields:
        None: يستمر التطبيق في العمل
    """
    # ==========================================
    # 🚀 STARTUP
    # ==========================================

    logger.info(
        "application_starting",
        extra={
            "environment": settings.APP_ENV,
            "debug": settings.DEBUG,
        },
    )

    # تهيئة قاعدة البيانات
    await init_db()

    # تسجيل مسارات الكولباك
    await register_routes()

    logger.info(
        "application_started",
        extra={
            "docs_url": "/docs",
            "redoc_url": "/redoc",
        },
    )

    yield

    # ==========================================
    # 🛑 SHUTDOWN
    # ==========================================

    logger.info(
        "application_shutting_down",
    )

    # إغلاق اتصال قاعدة البيانات
    await close_db()

    logger.info(
        "application_shutdown_complete",
    )


# ==============================================
# 🚀 CREATE FASTAPI APPLICATION
# ==============================================

app = FastAPI(
    title="MoulAI - مولاي",
    version="1.0.0",
    description="Agent-as-a-Service Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ==============================================
# 🌐 CORS MIDDLEWARE
# ==============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================
# 📋 INCLUDE ROUTERS
# ==============================================

# ✅ نقاط نهاية المديرين (API v1)
app.include_router(
    admin_router,
    prefix="/api/v1",
    tags=["Admins"],
)

# ✅ نقاط نهاية سجل أنشطة المديرين (API v1)
app.include_router(
    admin_log_router,
    prefix="/api/v1",
    tags=["Admin Logs"],
)

# ✅ نقاط نهاية جلسات المديرين (API v1)
app.include_router(
    admin_session_router,
    prefix="/api/v1",
    tags=["Admin Sessions"],
)

# ✅ نقاط نهاية المطاعم (API v1) - جميع الروترات الفرعية
app.include_router(
    restaurant_router,
    prefix="/api/v1",
    tags=["Restaurants"],
)

# ✅ نقاط نهاية المالكين (API v1)
app.include_router(
    owners_router,
    prefix="/api/v1",
    tags=["Owners"],
)

# ✅ نقاط نهاية طلبات التسجيل (API v1)
app.include_router(
    registration_requests_router,
    prefix="/api/v1",
    tags=["Registration Requests"],
)

# ✅ نقاط نهاية المدفوعات (API v1)
app.include_router(
    payments_router,
    prefix="/api/v1",
    tags=["Payments"],
)

# ✅ نقاط نهاية المنتجات (API v1)
app.include_router(
    products_router,
    prefix="/api/v1",
    tags=["Products"],
)

# ✅ نقاط نهاية الفروع (API v1)
app.include_router(
    branches_router,
    prefix="/api/v1",
    tags=["Branches"],
)

# ✅ نقاط نهاية التصنيفات (API v1)
app.include_router(
    categories_router,
    prefix="/api/v1",
    tags=["Categories"],
)

# ✅ نقاط نهاية الطلبات (API v1)
app.include_router(
    orders_router,
    prefix="/api/v1",
    tags=["Orders"],
)

# ✅ نقاط نهاية تفاصيل الطلب (API v1)
app.include_router(
    order_items_router,
    prefix="/api/v1",
    tags=["Order Items"],
)

# ✅ نقاط نهاية فروع المطاعم (API v1)
app.include_router(
    branches_router,
    prefix="/api/v1",
    tags=["Restaurant Branches"],
)

# ✅ نقاط نهاية مجموعات الخيارات (API v1)
app.include_router(
    option_groups_router,
    prefix="/api/v1",
    tags=["Option Groups"],
)

# ✅ نقاط نهاية خيارات المنتج (API v1)
app.include_router(
    product_options_router,
    prefix="/api/v1",
    tags=["Product Options"],
)

# ✅ نقاط نهاية المستخدمين (API v1)
app.include_router(
    users_router,
    prefix="/api/v1",
    tags=["Users"],
)

# ✅ Webhook (Telegram)
app.include_router(
    webhook_router,
    tags=["Webhook"],
)


# ==============================================
# 🏠 ROOT ENDPOINT
# ==============================================

@app.get("/")
async def root() -> dict:
    """
    الصفحة الرئيسية للتطبيق.
    
    Returns:
        dict: معلومات عن التطبيق
    """
    return {
        "message": "Welcome to MoulAI Platform",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "redoc": "/redoc",
    }


# ==============================================
# ❤️ HEALTH CHECK
# ==============================================

@app.get("/health")
async def health_check() -> dict:
    """
    التحقق من صحة التطبيق.
    
    Returns:
        dict: حالة التطبيق
    """
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }