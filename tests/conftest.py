# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🧪 PYTEST CONFIGURATION
# إعدادات مشتركة لجميع الاختبارات
# ==============================================

import asyncio
import time
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
)

import pytest
from httpx import (
    AsyncClient,
    ASGITransport,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.models.base import Base
from app.main import app


# ==============================================
# 🔧 TEST DATABASE
# ==============================================

TEST_DATABASE_URL = settings.DATABASE_URL + "_test"

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

TestingSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ==============================================
# 🔧 ASYNCIO FIXTURE
# ==============================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    إنشاء event loop للاختبارات غير المتزامنة.
    
    Returns:
        Generator[asyncio.AbstractEventLoop, None, None]: Event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================
# ✅ DB SESSION FIXTURE
# ==============================================

@pytest.fixture(scope="function")
async def db_session(
    cleanup_test_database: None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    إنشاء جلسة قاعدة بيانات اختبارية.
    
    ✅ rollback بعد كل اختبار لضمان عزل البيانات
    
    Yields:
        AsyncGenerator[AsyncSession, None]: جلسة قاعدة البيانات
    """
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ==============================================
# ✅ CLIENT FIXTURE
# ==============================================

@pytest.fixture(scope="function")
async def client(
    cleanup_test_database: None,
) -> AsyncGenerator[AsyncClient, None]:
    """
    إنشاء عميل اختبار HTTP مع جلسة قاعدة بيانات مستقلة لكل طلب.
    
    ✅ كل طلب HTTP يحصل على جلسة DB جديدة
    ✅ rollback بعد كل طلب لضمان عزل البيانات
    
    Yields:
        AsyncGenerator[AsyncClient, None]: عميل HTTP
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            try:
                yield session
            finally:
                await session.rollback()
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ==============================================
# 🔧 TEST DATABASE CLEANUP FIXTURE
# ==============================================

@pytest.fixture(scope="function")
async def cleanup_test_database() -> AsyncGenerator[None, None]:
    """
    تنظيف قاعدة البيانات التجريبية قبل وبعد كل اختبار.
    
    تستخدم واجهات API عمليات commit مستقلة؛ لذلك rollback الجلسة
    وحده لا يعزل الاختبارات.
    """
    import app.models

    table_names = ", ".join(
        f'"{table.name}"'
        for table in reversed(Base.metadata.sorted_tables)
    )

    async def truncate_all_tables() -> None:
        if not table_names:
            return

        async with engine.begin() as connection:
            await connection.execute(
                text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"),
            )

    await truncate_all_tables()
    yield
    await truncate_all_tables()


# ==============================================
# 📦 DATA FACTORIES - SAMPLE DATA
# ==============================================

@pytest.fixture
def sample_owner_data() -> Dict[str, Any]:
    """
    بيانات مالك نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات المالك
    """
    unique_id: int = int(time.time() * 1000) % 1000000000

    return {
        "chat_id": unique_id,
        "full_name": f"أحمد محمد {unique_id}",
        "phone": "0555123456",
        "email": f"ahmed_{unique_id}@example.com",
        "registration_status": "pending",
    }


@pytest.fixture
def sample_restaurant_data() -> Dict[str, Any]:
    """
    بيانات مطعم نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات المطعم
    """
    return {
        "name": "مطعم البيتزا الذهبية",
        "type": "restaurant",
        "phone": "+213551234567",
        "wilaya": "الجزائر",
        "lat": 36.7538,
        "lng": 3.0588,
        "is_active": True,
    }


@pytest.fixture
def sample_restaurant_group_data() -> Dict[str, Any]:
    """
    بيانات مجموعة مطاعم نموذجية للاختبار.
    
    ✅ لا يحتوي على is_active لأن RestaurantGroup لا يدعمه
    
    Returns:
        Dict[str, Any]: بيانات المجموعة
    """
    return {
        "name": "مجموعة المطاعم الذهبية",
    }


@pytest.fixture
def sample_restaurant_branch_data() -> Dict[str, Any]:
    """
    بيانات فرع مطعم نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات الفرع
    """
    return {
        "group_id": 1,
        "restaurant_id": 1,
    }


@pytest.fixture
def sample_bulk_branches_data() -> Dict[str, Any]:
    """
    بيانات فروع متعددة نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات الفروع المتعددة
    """
    return {
        "group_id": 1,
        "restaurant_ids": [1, 2, 3],
    }


@pytest.fixture
def sample_metric_data() -> Dict[str, Any]:
    """
    بيانات مقاييس نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات المقاييس
    """
    return {
        "products_count": 10,
        "categories_count": 5,
        "monthly_orders": 100,
        "average_order_value": 1500.00,
    }


@pytest.fixture
def sample_order_counter_data() -> Dict[str, Any]:
    """
    بيانات عداد طلبات نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات عداد الطلبات
    """
    return {
        "last_number": 0,
    }


@pytest.fixture
def sample_payment_settings_data() -> Dict[str, Any]:
    """
    بيانات إعدادات دفع نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات إعدادات الدفع
    """
    return {
        "allow_cash": True,
        "allow_card": True,
        "allow_ccp": False,
        "allow_baridimob": False,
        "allow_stripe": False,
        "allow_paypal": False,
    }


@pytest.fixture
def sample_order_data() -> Dict[str, Any]:
    """
    بيانات طلب نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات الطلب
    """
    return {
        "order_number": "RST1-000001",
        "order_type": "dine_in",
        "customer_name": "علي أحمد",
        "customer_phone": "0555123456",
        "delivery_address": None,
        "customer_note": "بدون بصل",
        "subtotal_amount": 100.00,
        "discount_amount": 0.00,
        "tax_amount": 0.00,
        "delivery_amount": 0.00,
        "total_amount": 100.00,
        "status": "pending",
    }


@pytest.fixture
def sample_product_data() -> Dict[str, Any]:
    """
    بيانات منتج نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات المنتج
    """
    return {
        "name": "بيتزا مارجريتا",
        "description": "بيتزا كلاسيكية بصلصة الطماطم والجبن",
        "price": 800.00,
        "image_url": None,
        "sort_order": 0,
        "is_available": True,
        "is_active": True,
    }


@pytest.fixture
def sample_category_data() -> Dict[str, Any]:
    """
    بيانات تصنيف نموذجية للاختبار.
    
    Returns:
        Dict[str, Any]: بيانات التصنيف
    """
    return {
        "name": "بيتزا",
        "description": "جميع أنواع البيتزا",
        "sort_order": 0,
        "is_active": True,
    }


@pytest.fixture
def sample_group_data() -> Dict[str, Any]:
    """
    بيانات مجموعة نموذجية للاختبار (متوافقة مع الاختبارات القديمة).
    
    ✅ لا يحتوي على is_active
    
    Returns:
        Dict[str, Any]: بيانات المجموعة
    """
    return {
        "name": "مجموعة المطاعم الذهبية",
    }


# ==============================================
# 🏗️ HELPER FUNCTIONS
# ==============================================

async def create_test_owner(
    db_session: AsyncSession,
    owner_data: Dict[str, Any],
) -> Any:
    """
    إنشاء مالك للاختبارات باستخدام DB مباشر.
    
    ⚠️ تستخدم فقط في إعدادات الاختبارات (setup)
    
    Args:
        db_session: جلسة قاعدة البيانات
        owner_data: بيانات المالك
        
    Returns:
        Any: كائن المالك المنشأ
    """
    from app.models.owner import Owner

    owner = Owner(**owner_data)
    db_session.add(owner)
    await db_session.flush()
    await db_session.refresh(owner)
    return owner


async def create_test_restaurant(
    db_session: AsyncSession,
    restaurant_data: Dict[str, Any],
    owner_id: int,
) -> Any:
    """
    إنشاء مطعم للاختبارات باستخدام DB مباشر.
    
    ⚠️ تستخدم فقط في إعدادات الاختبارات (setup)
    
    Args:
        db_session: جلسة قاعدة البيانات
        restaurant_data: بيانات المطعم
        owner_id: معرف المالك
        
    Returns:
        Any: كائن المطعم المنشأ
    """
    from app.models.restaurant import Restaurant

    restaurant = Restaurant(
        **{**restaurant_data, "owner_id": owner_id}
    )
    db_session.add(restaurant)
    await db_session.flush()
    await db_session.refresh(restaurant)
    return restaurant


async def create_test_group(
    db_session: AsyncSession,
    group_data: Dict[str, Any],
    owner_id: int,
) -> Any:
    """
    إنشاء مجموعة مطاعم للاختبارات باستخدام DB مباشر.
    
    ⚠️ تستخدم فقط في إعدادات الاختبارات (setup)
    
    Args:
        db_session: جلسة قاعدة البيانات
        group_data: بيانات المجموعة
        owner_id: معرف المالك
        
    Returns:
        Any: كائن المجموعة المنشأ
    """
    from app.models.restaurant_group import RestaurantGroup

    group = RestaurantGroup(
        **{**group_data, "owner_id": owner_id}
    )
    db_session.add(group)
    await db_session.flush()
    await db_session.refresh(group)
    return group


async def create_test_branch(
    db_session: AsyncSession,
    group_id: int,
    restaurant_id: int,
) -> Any:
    """
    إنشاء فرع مطعم للاختبارات باستخدام DB مباشر.
    
    ⚠️ تستخدم فقط في إعدادات الاختبارات (setup)
    
    Args:
        db_session: جلسة قاعدة البيانات
        group_id: معرف المجموعة
        restaurant_id: معرف المطعم
        
    Returns:
        Any: كائن الفرع المنشأ
    """
    from app.models.restaurant_group import RestaurantBranch

    branch = RestaurantBranch(
        group_id=group_id,
        restaurant_id=restaurant_id,
    )
    db_session.add(branch)
    await db_session.flush()
    await db_session.refresh(branch)
    return branch


# ==============================================
# 📋 EXPORTS
# ==============================================

__all__ = [
    # Fixtures
    "event_loop",
    "db_session",
    "client",
    # Sample Data
    "sample_owner_data",
    "sample_restaurant_data",
    "sample_restaurant_group_data",
    "sample_restaurant_branch_data",
    "sample_bulk_branches_data",
    "sample_metric_data",
    "sample_order_counter_data",
    "sample_payment_settings_data",
    "sample_order_data",
    "sample_product_data",
    "sample_category_data",
    "sample_group_data",
    # Helper Functions
    "create_test_owner",
    "create_test_restaurant",
    "create_test_group",
    "create_test_branch",
]
