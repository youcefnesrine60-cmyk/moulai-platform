# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS / PRODUCT SERVICE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for product service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# 🍔 PRODUCT SERVICE
# Business Logic Layer - منطق الأعمال للمنتجات
#
# - إنشاء منتج
# - قراءة المنتج
# - قراءة منتجات المطعم
# - تحديث المنتج
# - تفعيل/إلغاء تفعيل المنتج
# - حذف المنتج
#
# Async SQLAlchemy Version
# ==============================================

from typing import (
    Any,
    TypeAlias,
)

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.core.security import sanitize_input
from app.core.security.tenant_scope import bind_owner_scope
from app.models.category import Category
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.restaurant import Restaurant
from app.repositories.products_repo import ProductRepository
from app.repositories.restaurant.restaurant_metrics_repo import (
    RestaurantMetricsRepository,
)
from app.schemas.product import (
    ProductAvailabilityUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductSummary,
    ProductUpdate,
)
from app.services.business.feature_usage_counter_engine import (
    decrease_usage,
    increase_usage,
)

# ==============================================
# 🧩 CONSTANTS
# ==============================================

PRODUCT_FEATURE_ID = 1
MAX_PRODUCTS_PER_RESTAURANT = 100
MAX_PRODUCT_PRICE = 10000000.0  # 10,000,000 DZD

# ==============================================
# 🧩 TYPES
# ==============================================

ProductData: TypeAlias = dict[str, Any]
ProductList: TypeAlias = list[Product]


# ==============================================
# BASE SELECT
# ==============================================


def _base_product_category_select() -> Select[tuple[int]]:
    """Resolve a category through its restaurant before product mutations."""
    return select(Category.id).join(Restaurant, Category.restaurant_id == Restaurant.id)


# ==============================================
# 🍔 PRODUCT SERVICE
# ==============================================


class ProductService:
    """
    خدمة المنتجات - تدير منطق الأعمال للمنتجات.

    مسؤولة عن:
        - إنشاء وإدارة المنتجات
        - تحديث حالة التوفر
        - تحديث مقاييس المطعم
        - إدارة عداد استخدام الميزات

    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع المنتجات
        metrics_repo: مستودع مقاييس المطعم
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        *,
        session: AsyncSession,
        owner_id: int,
    ) -> None:
        """
        تهيئة خدمة المنتجات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        bind_owner_scope(session=session, owner_id=owner_id)
        self.owner_id = owner_id
        self.session = session
        self.repo = ProductRepository(session)
        self.metrics_repo = RestaurantMetricsRepository(session)

    # ==========================================
    # 🛠️ PRIVATE HELPERS
    # ==========================================

    # ==============================================
    # REQUIRE PRODUCT CATEGORY RESTAURANT
    # ==============================================

    async def _require_category_restaurant(
        self,
        *,
        category_id: int,
        restaurant_id: int,
    ) -> None:
        """Reject a category outside the product restaurant before any mutation."""
        result = await self.session.execute(
            _base_product_category_select().where(
                Category.id == category_id,
                Category.restaurant_id == restaurant_id,
                Restaurant.owner_id == self.owner_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError(message="Category not found in this restaurant")

    # ==============================================
    # COUNT ORDERS BY PRODUCT
    # ==============================================

    async def _count_orders_by_product(
        self,
        *,
        product_id: int,
    ) -> int:
        """
        حساب عدد الطلبات المرتبطة بمنتج معين.

        ✅ استخدام SQLAlchemy مباشرة عبر OrderItem

        Args:
            product_id: معرف المنتج

        Returns:
            عدد الطلبات المرتبطة
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(OrderItem)
            .where(OrderItem.product_id == product_id),
        )

        return result.scalar_one() or 0

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        product_id: int,
    ) -> ProductResponse:
        """
        الحصول على منتج بالمعرف.

        Args:
            product_id: معرف المنتج

        Returns:
            ProductResponse: بيانات المنتج

        Raises:
            NotFoundError: إذا لم يتم العثور على المنتج
        """
        logger.info(
            "product_service_get_by_id",
            extra={"product_id": product_id},
        )

        product = await self.repo.get_by_id(id=product_id)

        if not product:
            raise NotFoundError(
                message=f"المنتج بـ ID '{product_id}' غير موجود",
            )

        return ProductResponse.model_validate(product)

    # ==============================================
    # GET BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
        only_available: bool = True,
    ) -> ProductListResponse:
        """
        الحصول على منتجات مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_available: جلب المنتجات المتاحة فقط

        Returns:
            ProductListResponse: قائمة المنتجات مع الإحصائيات
        """
        logger.info(
            "product_service_get_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
                "only_available": only_available,
            },
        )

        products = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
            only_available=only_available,
        )

        total = await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_available=only_available,
        )

        return ProductListResponse(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET BY CATEGORY
    # ==============================================

    async def get_by_category(
        self,
        *,
        category_id: int,
        skip: int = 0,
        limit: int = 100,
        only_available: bool = True,
    ) -> ProductListResponse:
        """
        الحصول على منتجات تصنيف معين.

        Args:
            category_id: معرف التصنيف
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_available: جلب المنتجات المتاحة فقط

        Returns:
            ProductListResponse: قائمة المنتجات مع الإحصائيات
        """
        logger.info(
            "product_service_get_by_category",
            extra={
                "category_id": category_id,
                "skip": skip,
                "limit": limit,
                "only_available": only_available,
            },
        )

        products = await self.repo.get_by_category_id(
            category_id=category_id,
            skip=skip,
            limit=limit,
            only_available=only_available,
        )

        total = await self.repo.count_by_category(
            category_id=category_id,
            only_available=only_available,
        )

        return ProductListResponse(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        restaurant_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> ProductListResponse:
        """
        البحث عن منتجات.

        Args:
            query: نص البحث
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            ProductListResponse: قائمة المنتجات مع الإحصائيات
        """
        clean_query = sanitize_input(query)

        logger.info(
            "product_service_search",
            extra={
                "search_query": clean_query,
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
            },
        )

        products = await self.repo.search(
            query=clean_query,
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )

        total = len(products)

        return ProductListResponse(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET WITH DETAILS
    # ==============================================

    async def get_with_details(
        self,
        *,
        product_id: int,
    ) -> Product | None:
        """
        الحصول على منتج مع جميع علاقاته.

        Args:
            product_id: معرف المنتج

        Returns:
            Optional[Product]: كائن Product مع العلاقات أو None
        """
        logger.info(
            "product_service_get_with_details",
            extra={"product_id": product_id},
        )

        return await self.repo.get_with_details(
            product_id=product_id,
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
        only_available: bool = True,
    ) -> int:
        """
        حساب عدد منتجات مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            only_available: حساب المنتجات المتاحة فقط

        Returns:
            int: عدد المنتجات
        """
        return await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_available=only_available,
        )

    # ==============================================
    # COUNT BY CATEGORY
    # ==============================================

    async def count_by_category(
        self,
        *,
        category_id: int,
        only_available: bool = True,
    ) -> int:
        """
        حساب عدد منتجات تصنيف معين.

        Args:
            category_id: معرف التصنيف
            only_available: حساب المنتجات المتاحة فقط

        Returns:
            int: عدد المنتجات
        """
        return await self.repo.count_by_category(
            category_id=category_id,
            only_available=only_available,
        )

    # ==============================================
    # GET PRODUCT SUMMARY
    # ==============================================

    async def get_product_summary(
        self,
        *,
        restaurant_id: int,
    ) -> ProductSummary:
        """
        الحصول على ملخص المنتجات لمطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            ProductSummary: ملخص المنتجات
        """
        logger.info(
            "product_service_get_product_summary",
            extra={"restaurant_id": restaurant_id},
        )

        total = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_available=False,
        )

        available = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_available=True,
        )

        unavailable = total - available

        # ✅ الحصول على المنتجات لحساب الأسعار
        products = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            limit=10000,
            only_available=False,
        )

        total_price = 0.0
        min_price = 0.0
        max_price = 0.0

        if products:
            prices = [float(p.price) for p in products]
            total_price = sum(prices)
            min_price = min(prices)
            max_price = max(prices)

        avg_price = total_price / len(products) if products else 0.0

        return ProductSummary(
            total_products=total,
            available_products=available,
            unavailable_products=unavailable,
            total_price=round(total_price, 2),
            avg_price=round(avg_price, 2),
            min_price=round(min_price, 2),
            max_price=round(max_price, 2),
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE PRODUCT
    # ==============================================

    async def create_product(
        self,
        *,
        product_data: ProductCreate,
        restaurant_id: int,
    ) -> ProductResponse:
        """
        إنشاء منتج جديد.

        Args:
            product_data: بيانات المنتج
            restaurant_id: معرف المطعم

        Returns:
            ProductResponse: بيانات المنتج المنشأ

        Raises:
            ConflictError: إذا كان الاسم مكرراً للمطعم
            ValidationError: إذا كانت البيانات غير صالحة
        """
        await self._require_category_restaurant(
            category_id=product_data.category_id,
            restaurant_id=restaurant_id,
        )
        name = sanitize_input(product_data.name)
        description = (
            sanitize_input(product_data.description)
            if product_data.description
            else None
        )

        logger.info(
            "product_service_create",
            extra={
                "restaurant_id": restaurant_id,
                "product_name": name,
                "price": product_data.price,
            },
        )

        # 1️⃣ التحقق من صحة السعر
        if product_data.price <= 0:
            raise ValidationError(
                message="سعر المنتج يجب أن يكون أكبر من الصفر",
            )

        if product_data.price > MAX_PRODUCT_PRICE:
            raise ValidationError(
                message=(
                    f"سعر المنتج يتجاوز الحد الأقصى المسموح به "
                    f"({MAX_PRODUCT_PRICE})"
                ),
            )

        # 2️⃣ التحقق من الحد الأقصى للمنتجات
        current_count = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_available=False,
        )

        if current_count >= MAX_PRODUCTS_PER_RESTAURANT:
            raise ValidationError(
                message=(
                    f"تجاوزت الحد الأقصى للمنتجات " f"({MAX_PRODUCTS_PER_RESTAURANT})"
                ),
                details={
                    "restaurant_id": restaurant_id,
                    "current_count": current_count,
                    "max_allowed": MAX_PRODUCTS_PER_RESTAURANT,
                },
            )

        # 3️⃣ التحقق من عدم وجود منتج بنفس الاسم
        existing = await self.repo.get_by_name(
            restaurant_id=restaurant_id,
            name=name,
        )

        if existing:
            raise ConflictError(
                message=f"المنتج '{name}' موجود بالفعل لهذا المطعم",
            )

        # 4️⃣ إنشاء المنتج
        data: ProductData = {
            "restaurant_id": restaurant_id,
            "category_id": product_data.category_id,
            "name": name,
            "description": description,
            "price": product_data.price,
            "image_url": product_data.image_url,
            "sort_order": product_data.sort_order or 0,
            "is_available": True,
        }

        product = await self.repo.create(data=data)

        # 5️⃣ زيادة عداد استخدام الميزة (مع session)
        await increase_usage(
            session=self.session,
            restaurant_id=restaurant_id,
            feature_id=PRODUCT_FEATURE_ID,
        )

        # 6️⃣ تحديث مقاييس المطعم
        await self._update_restaurant_metrics(
            restaurant_id=restaurant_id,
            action="product_created",
        )

        logger.info(
            "product_created_successfully",
            extra={
                "product_id": product.id,
                "restaurant_id": restaurant_id,
            },
        )

        return ProductResponse.model_validate(product)

    # ==============================================
    # UPDATE PRODUCT
    # ==============================================

    async def update_product(
        self,
        *,
        product_id: int,
        update_data: ProductUpdate,
    ) -> ProductResponse:
        """
        تحديث منتج.

        Args:
            product_id: معرف المنتج
            update_data: بيانات التحديث

        Returns:
            ProductResponse: بيانات المنتج المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المنتج
            ConflictError: إذا كان الاسم مكرراً
        """
        logger.info(
            "product_service_update",
            extra={
                "product_id": product_id,
                "update_fields": list(
                    update_data.model_dump(exclude_unset=True).keys()
                ),
            },
        )

        # 1️⃣ التحقق من وجود المنتج
        existing_product = await self.repo.get_by_id(id=product_id)

        if not existing_product:
            raise NotFoundError(
                message=f"المنتج بـ ID '{product_id}' غير موجود",
            )

        # 2️⃣ تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)
        if "category_id" in updates:
            await self._require_category_restaurant(
                category_id=updates["category_id"],
                restaurant_id=existing_product.restaurant_id,
            )

        # 3️⃣ تنظيف البيانات
        if "name" in updates:
            updates["name"] = sanitize_input(updates["name"])

            duplicate = await self.repo.get_by_name(
                restaurant_id=existing_product.restaurant_id,
                name=updates["name"],
            )

            if duplicate and duplicate.id != product_id:
                raise ConflictError(
                    message=(
                        f"المنتج '{updates['name']}' " f"موجود بالفعل لهذا المطعم"
                    ),
                )

        if "description" in updates:
            updates["description"] = sanitize_input(updates["description"])

        if "price" in updates:
            if updates["price"] <= 0:
                raise ValidationError(
                    message="سعر المنتج يجب أن يكون أكبر من الصفر",
                )

            if updates["price"] > MAX_PRODUCT_PRICE:
                raise ValidationError(
                    message=(
                        f"سعر المنتج يتجاوز الحد الأقصى المسموح به "
                        f"({MAX_PRODUCT_PRICE})"
                    ),
                )

        # 4️⃣ تحديث المنتج
        product = await self.repo.update(
            id=product_id,
            data=updates,
        )

        if not product:
            raise NotFoundError(
                message=f"المنتج بـ ID '{product_id}' غير موجود",
            )

        logger.info(
            "product_updated_successfully",
            extra={
                "product_id": product_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return ProductResponse.model_validate(product)

    # ==============================================
    # UPDATE AVAILABILITY
    # ==============================================

    async def update_availability(
        self,
        *,
        product_id: int,
        availability_data: ProductAvailabilityUpdate,
    ) -> ProductResponse:
        """
        تحديث حالة توفر المنتج.

        Args:
            product_id: معرف المنتج
            availability_data: بيانات حالة التوفر

        Returns:
            ProductResponse: بيانات المنتج المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المنتج
        """
        logger.info(
            "product_service_update_availability",
            extra={
                "product_id": product_id,
                "is_available": availability_data.is_available,
            },
        )

        product = await self.repo.update_availability(
            product_id=product_id,
            is_available=availability_data.is_available,
        )

        if not product:
            raise NotFoundError(
                message=f"المنتج بـ ID '{product_id}' غير موجود",
            )

        logger.info(
            "product_availability_updated",
            extra={
                "product_id": product_id,
                "is_available": availability_data.is_available,
            },
        )

        return ProductResponse.model_validate(product)

    # ==============================================
    # ENABLE PRODUCT
    # ==============================================

    async def enable_product(
        self,
        *,
        product_id: int,
    ) -> ProductResponse:
        """
        تفعيل المنتج.

        Args:
            product_id: معرف المنتج

        Returns:
            ProductResponse: بيانات المنتج المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المنتج
        """
        logger.info(
            "product_service_enable",
            extra={"product_id": product_id},
        )

        availability_data = ProductAvailabilityUpdate(is_available=True)

        return await self.update_availability(
            product_id=product_id,
            availability_data=availability_data,
        )

    # ==============================================
    # DISABLE PRODUCT
    # ==============================================

    async def disable_product(
        self,
        *,
        product_id: int,
    ) -> ProductResponse:
        """
        إلغاء تفعيل المنتج.

        Args:
            product_id: معرف المنتج

        Returns:
            ProductResponse: بيانات المنتج المحدث

        Raises:
            NotFoundError: إذا لم يتم العثور على المنتج
        """
        logger.info(
            "product_service_disable",
            extra={"product_id": product_id},
        )

        availability_data = ProductAvailabilityUpdate(is_available=False)

        return await self.update_availability(
            product_id=product_id,
            availability_data=availability_data,
        )

    # ==============================================
    # DELETE PRODUCT
    # ==============================================

    async def delete_product(
        self,
        *,
        product_id: int,
    ) -> None:
        """
        حذف منتج.

        Args:
            product_id: معرف المنتج

        Raises:
            NotFoundError: إذا لم يتم العثور على المنتج
            ValidationError: إذا كان المنتج مرتبطاً بطلبات
        """
        logger.info(
            "product_service_delete",
            extra={"product_id": product_id},
        )

        product = await self.repo.get_by_id(id=product_id)

        if not product:
            raise NotFoundError(
                message=f"المنتج بـ ID '{product_id}' غير موجود",
            )

        restaurant_id = product.restaurant_id

        # 1️⃣ التحقق من عدم وجود طلبات مرتبطة
        orders_count = await self._count_orders_by_product(
            product_id=product_id,
        )

        if orders_count > 0:
            raise ValidationError(
                message="لا يمكن حذف المنتج لأنه مرتبط بطلبات",
                details={
                    "product_id": product_id,
                    "orders_count": orders_count,
                },
            )

        # 2️⃣ حذف المنتج
        await self.repo.delete(id=product_id)

        # 3️⃣ تحديث مقاييس المطعم
        await self._update_restaurant_metrics(
            restaurant_id=restaurant_id,
            action="product_deleted",
        )

        # 4️⃣ تقليل عداد استخدام الميزة (مع session)
        await decrease_usage(
            session=self.session,
            restaurant_id=restaurant_id,
            feature_id=PRODUCT_FEATURE_ID,
        )

        logger.info(
            "product_deleted_successfully",
            extra={
                "product_id": product_id,
                "restaurant_id": restaurant_id,
            },
        )

    # ==========================================
    # 🛠️ PRIVATE HELPERS
    # ==========================================

    # ==============================================
    # UPDATE RESTAURANT METRICS
    # ==============================================

    async def _update_restaurant_metrics(
        self,
        *,
        restaurant_id: int,
        action: str,
    ) -> None:
        """
        تحديث مقاييس المطعم.

        ✅ نستخدم RestaurantMetricsRepository
        ✅ increment/decrement بدلاً من update اليدوي

        Args:
            restaurant_id: معرف المطعم
            action: نوع الإجراء (product_created, product_deleted)
        """
        try:
            if action == "product_created":
                await self.metrics_repo.increment_products_count(
                    restaurant_id=restaurant_id,
                    amount=1,
                )
            elif action == "product_deleted":
                await self.metrics_repo.decrement_products_count(
                    restaurant_id=restaurant_id,
                    amount=1,
                )

            logger.info(
                "restaurant_metrics_updated",
                extra={
                    "restaurant_id": restaurant_id,
                    "action": action,
                },
            )

        except Exception as e:
            logger.warning(
                "restaurant_metrics_update_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "action": action,
                    "error": str(e),
                },
            )


# ==============================================
