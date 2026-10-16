# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / SERVICES / BUSINESS
# / CATEGORY SERVICE
# ==============================================

"""MoulAI operational module for category service.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# ðŸ“‚ CATEGORY SERVICE
# Business Logic Layer - Ù…Ù†Ø·Ù‚ Ø§Ù„Ø£Ø¹Ù…Ø§Ù„ Ù„Ù„ØªØµÙ†ÙŠÙØ§Øª
#
# - Ø¥Ù†Ø´Ø§Ø¡ ØªØµÙ†ÙŠÙ
# - Ù‚Ø±Ø§Ø¡Ø© Ø§Ù„ØªØµÙ†ÙŠÙ
# - Ù‚Ø±Ø§Ø¡Ø© ØªØµÙ†ÙŠÙØ§Øª Ø§Ù„Ù…Ø·Ø¹Ù…
# - Ø­Ø°Ù Ø§Ù„ØªØµÙ†ÙŠÙ
#
# Async SQLAlchemy Version
# ==============================================

from typing import (
    Any,
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logger import logger
from app.core.security import sanitize_input
from app.models.category import Category
from app.repositories.categories_repo import CategoriesRepository
from app.repositories.features_repo import FeatureRepository
from app.repositories.products_repo import ProductRepository
from app.repositories.restaurant.restaurant_metrics_repo import (
    RestaurantMetricsRepository,
)
from app.schemas.categories import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategorySummary,
    CategoryUpdate,
)
from app.services.business.feature_usage_counter_engine import (
    decrease_usage,
    increase_usage,
)

# ==============================================
# ðŸ§© CONSTANTS
# ==============================================

CATEGORY_FEATURE_CODE = "categories"
MAX_CATEGORIES_PER_RESTAURANT = 20

# ==============================================
# ðŸ§© TYPES
# ==============================================

CategoryData = dict[str, Any]
CategoryList = list[Category]

# ==============================================
# ðŸ“‚ CATEGORY SERVICE
# ==============================================


class CategoryService:
    """
    Ø®Ø¯Ù…Ø© Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª - ØªØ¯ÙŠØ± Ù…Ù†Ø·Ù‚ Ø§Ù„Ø£Ø¹Ù…Ø§Ù„ Ù„Ù„ØªØµÙ†ÙŠÙØ§Øª.

    Ù…Ø³Ø¤ÙˆÙ„Ø© Ø¹Ù†:
        - Ø¥Ù†Ø´Ø§Ø¡ ÙˆØ¥Ø¯Ø§Ø±Ø© Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª
        - ØªØ­Ø¯ÙŠØ« ØªØ±ØªÙŠØ¨ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª
        - ØªØ­Ø¯ÙŠØ« Ù…Ù‚Ø§ÙŠÙŠØ³ Ø§Ù„Ù…Ø·Ø¹Ù…
        - Ø¥Ø¯Ø§Ø±Ø© Ø¹Ø¯Ø§Ø¯ Ø§Ø³ØªØ®Ø¯Ø§Ù… Ø§Ù„Ù…ÙŠØ²Ø§Øª

    Attributes:
        session: Ø¬Ù„Ø³Ø© Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª ØºÙŠØ± Ø§Ù„Ù…ØªØ²Ø§Ù…Ù†Ø©
        repo: Ù…Ø³ØªÙˆØ¯Ø¹ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª
        product_repo: Ù…Ø³ØªÙˆØ¯Ø¹ Ø§Ù„Ù…Ù†ØªØ¬Ø§Øª
        metrics_repo: Ù…Ø³ØªÙˆØ¯Ø¹ Ù…Ù‚Ø§ÙŠÙŠØ³ Ø§Ù„Ù…Ø·Ø¹Ù…
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        ØªÙ‡ÙŠØ¦Ø© Ø®Ø¯Ù…Ø© Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª.

        Args:
            session: Ø¬Ù„Ø³Ø© Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª ØºÙŠØ± Ø§Ù„Ù…ØªØ²Ø§Ù…Ù†Ø©
        """
        self.session = session
        self.repo = CategoriesRepository(session)
        self.product_repo = ProductRepository(session)
        self.metrics_repo = RestaurantMetricsRepository(session)
        self.feature_repo = FeatureRepository(session)

    # ==========================================
    # ðŸ› ï¸ PRIVATE HELPERS
    # ==========================================

    # ==============================================
    # RESOLVE CATEGORY FEATURE
    # ==============================================

    async def _get_category_feature_id(self, *, restaurant_id: int) -> int | None:
        """Return the optional category feature identifier without assuming database IDs."""
        feature = await self.feature_repo.get_by_code(code=CATEGORY_FEATURE_CODE)
        if feature is None:
            logger.warning(
                "category_feature_not_configured",
                extra={
                    "restaurant_id": restaurant_id,
                    "feature_code": CATEGORY_FEATURE_CODE,
                },
            )
            return None
        return feature.id

    # ==============================================
    # COUNT PRODUCTS IN CATEGORY
    # ==============================================

    async def _count_products_in_category(
        self,
        *,
        category_id: int,
    ) -> int:
        """
        Ø­Ø³Ø§Ø¨ Ø¹Ø¯Ø¯ Ø§Ù„Ù…Ù†ØªØ¬Ø§Øª ÙÙŠ ØªØµÙ†ÙŠÙ Ù…Ø¹ÙŠÙ†.

        âœ… Ù†Ø³ØªØ®Ø¯Ù… ProductRepository.count_by_category

        Args:
            category_id: Ù…Ø¹Ø±Ù Ø§Ù„ØªØµÙ†ÙŠÙ

        Returns:
            Ø¹Ø¯Ø¯ Ø§Ù„Ù…Ù†ØªØ¬Ø§Øª
        """
        return await self.product_repo.count_by_category(
            category_id=category_id,
            only_available=False,
        )

    # ==========================================
    # ðŸ“– QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        category_id: int,
    ) -> CategoryResponse:
        """
        Ø§Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ ØªØµÙ†ÙŠÙ Ø¨Ø§Ù„Ù…Ø¹Ø±Ù.

        Args:
            category_id: Ù…Ø¹Ø±Ù Ø§Ù„ØªØµÙ†ÙŠÙ

        Returns:
            CategoryResponse: Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„ØªØµÙ†ÙŠÙ

        Raises:
            NotFoundError: Ø¥Ø°Ø§ Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø§Ù„ØªØµÙ†ÙŠÙ
        """
        logger.info(
            "category_service_get_by_id",
            extra={"category_id": category_id},
        )

        category = await self.repo.get_by_id(id=category_id)

        if not category:
            raise NotFoundError(
                message=f"Ø§Ù„ØªØµÙ†ÙŠÙ Ø¨Ù€ ID '{category_id}' ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯",
            )

        return CategoryResponse.model_validate(category)

    # ==============================================
    # GET BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> CategoryListResponse:
        """
        Ø§Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ ØªØµÙ†ÙŠÙØ§Øª Ù…Ø·Ø¹Ù… Ù…Ø¹ÙŠÙ†.

        Args:
            restaurant_id: Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø·Ø¹Ù…
            skip: Ø¹Ø¯Ø¯ Ø§Ù„Ø³Ø¬Ù„Ø§Øª Ù„Ù„ØªØ®Ø·ÙŠ
            limit: Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ù‚ØµÙ‰ Ù„Ù„Ø³Ø¬Ù„Ø§Øª

        Returns:
            CategoryListResponse: Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª Ù…Ø¹ Ø§Ù„Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª
        """
        logger.info(
            "category_service_get_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
            },
        )

        categories = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )

        total = await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

        return CategoryListResponse(
            items=[CategoryResponse.model_validate(c) for c in categories],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET BY NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        restaurant_id: int,
        name: str,
    ) -> Category | None:
        """
        Ø§Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ ØªØµÙ†ÙŠÙ Ø¨ÙˆØ§Ø³Ø·Ø© Ø§Ø³Ù…Ù‡.

        Args:
            restaurant_id: Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø·Ø¹Ù…
            name: Ø§Ø³Ù… Ø§Ù„ØªØµÙ†ÙŠÙ

        Returns:
            ÙƒØ§Ø¦Ù† Category Ø£Ùˆ None
        """
        logger.info(
            "category_service_get_by_name",
            extra={
                "restaurant_id": restaurant_id,
                "category_name": name,
            },
        )

        return await self.repo.get_by_name(
            restaurant_id=restaurant_id,
            name=name,
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
    ) -> CategoryListResponse:
        """
        Ø§Ù„Ø¨Ø­Ø« Ø¹Ù† ØªØµÙ†ÙŠÙØ§Øª.

        Args:
            query: Ù†Øµ Ø§Ù„Ø¨Ø­Ø«
            restaurant_id: Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø·Ø¹Ù… (Ø§Ø®ØªÙŠØ§Ø±ÙŠ)
            skip: Ø¹Ø¯Ø¯ Ø§Ù„Ø³Ø¬Ù„Ø§Øª Ù„Ù„ØªØ®Ø·ÙŠ
            limit: Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ù‚ØµÙ‰ Ù„Ù„Ø³Ø¬Ù„Ø§Øª

        Returns:
            CategoryListResponse: Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª Ù…Ø¹ Ø§Ù„Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª
        """
        clean_query = sanitize_input(query)

        logger.info(
            "category_service_search",
            extra={
                "search_query": clean_query,
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
            },
        )

        categories = await self.repo.search(
            query=clean_query,
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )

        total = len(categories)

        return CategoryListResponse(
            items=[CategoryResponse.model_validate(c) for c in categories],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ðŸ“Š STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        Ø­Ø³Ø§Ø¨ Ø¹Ø¯Ø¯ ØªØµÙ†ÙŠÙØ§Øª Ù…Ø·Ø¹Ù… Ù…Ø¹ÙŠÙ†.

        Args:
            restaurant_id: Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø·Ø¹Ù…

        Returns:
            int: Ø¹Ø¯Ø¯ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª
        """
        return await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

    # ==============================================
    # GET CATEGORY SUMMARY
    # ==============================================

    async def get_category_summary(
        self,
        *,
        restaurant_id: int,
    ) -> CategorySummary:
        """
        Ø§Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ Ù…Ù„Ø®Øµ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª Ù„Ù…Ø·Ø¹Ù… Ù…Ø¹ÙŠÙ†.

        Args:
            restaurant_id: Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø·Ø¹Ù…

        Returns:
            CategorySummary: Ù…Ù„Ø®Øµ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª
        """
        logger.info(
            "category_service_get_category_summary",
            extra={"restaurant_id": restaurant_id},
        )

        total = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

        # âœ… Ø§Ù„Ø­ØµÙˆÙ„ Ø¹Ù„Ù‰ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª Ù…Ø¹ Ø¹Ø¯Ø¯ Ø§Ù„Ù…Ù†ØªØ¬Ø§Øª Ù„ÙƒÙ„ ØªØµÙ†ÙŠÙ
        categories = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            limit=1000,
        )

        total_products = 0
        categories_with_products_count = 0

        for category in categories:
            product_count = await self._count_products_in_category(
                category_id=category.id,
            )

            total_products += product_count

            if product_count > 0:
                categories_with_products_count += 1

        avg_products_per_category = total_products / total if total > 0 else 0.0

        return CategorySummary(
            total_categories=total,
            categories_with_products=categories_with_products_count,
            empty_categories=total - categories_with_products_count,
            total_products=total_products,
            avg_products_per_category=round(avg_products_per_category, 2),
        )

    # ==========================================
    # âœï¸ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE CATEGORY
    # ==============================================

    async def create_category(
        self,
        *,
        restaurant_id: int,
        category_data: CategoryCreate,
    ) -> CategoryResponse:
        """
        Ø¥Ù†Ø´Ø§Ø¡ ØªØµÙ†ÙŠÙ Ø¬Ø¯ÙŠØ¯.

        Args:
            restaurant_id: Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø·Ø¹Ù…
            category_data: Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„ØªØµÙ†ÙŠÙ

        Returns:
            CategoryResponse: Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„ØªØµÙ†ÙŠÙ Ø§Ù„Ù…Ù†Ø´Ø£

        Raises:
            ConflictError: Ø¥Ø°Ø§ ÙƒØ§Ù† Ø§Ù„Ø§Ø³Ù… Ù…ÙˆØ¬ÙˆØ¯Ø§Ù‹ Ù…Ø³Ø¨Ù‚Ø§Ù‹
            ValidationError: Ø¥Ø°Ø§ ÙƒØ§Ù†Øª Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª ØºÙŠØ± ØµØ­ÙŠØ­Ø©
        """
        name = sanitize_input(category_data.name)

        logger.info(
            "category_service_create",
            extra={
                "restaurant_id": restaurant_id,
                "category_name": name,
            },
        )

        # 1ï¸âƒ£ Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ù‚ØµÙ‰ Ù„Ù„ØªØµÙ†ÙŠÙØ§Øª
        current_count = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

        if current_count >= MAX_CATEGORIES_PER_RESTAURANT:
            raise ValidationError(
                message=(
                    f"ØªØ¬Ø§ÙˆØ²Øª Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ù‚ØµÙ‰ Ù„Ù„ØªØµÙ†ÙŠÙØ§Øª "
                    f"({MAX_CATEGORIES_PER_RESTAURANT})"
                ),
                details={
                    "restaurant_id": restaurant_id,
                    "current_count": current_count,
                    "max_allowed": MAX_CATEGORIES_PER_RESTAURANT,
                },
            )

        # 2ï¸âƒ£ Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø¹Ø¯Ù… ÙˆØ¬ÙˆØ¯ ØªØµÙ†ÙŠÙ Ø¨Ù†ÙØ³ Ø§Ù„Ø§Ø³Ù…
        existing = await self.repo.get_by_name(
            restaurant_id=restaurant_id,
            name=name,
        )

        if existing:
            raise ConflictError(
                message=f"ÙŠÙˆØ¬Ø¯ ØªØµÙ†ÙŠÙ Ø¨Ø§Ø³Ù… '{name}' Ø¨Ø§Ù„ÙØ¹Ù„ Ù„Ù‡Ø°Ø§ Ø§Ù„Ù…Ø·Ø¹Ù…",
            )

        # 3ï¸âƒ£ Ø¥Ù†Ø´Ø§Ø¡ Ø§Ù„ØªØµÙ†ÙŠÙ
        data: CategoryData = {
            "restaurant_id": restaurant_id,
            "name": name,
            "sort_order": category_data.sort_order or 0,
        }

        category = await self.repo.create(data=data)

        # 4ï¸âƒ£ Ø²ÙŠØ§Ø¯Ø© Ø¹Ø¯Ø§Ø¯ Ø§Ø³ØªØ®Ø¯Ø§Ù… Ø§Ù„Ù…ÙŠØ²Ø© (Ù…Ø¹ session)
        feature_id = await self._get_category_feature_id(restaurant_id=restaurant_id)
        if feature_id is not None:
            await increase_usage(
                session=self.session,
                restaurant_id=restaurant_id,
                feature_id=feature_id,
            )

        # 5ï¸âƒ£ ØªØ­Ø¯ÙŠØ« Ù…Ù‚Ø§ÙŠÙŠØ³ Ø§Ù„Ù…Ø·Ø¹Ù…
        await self._update_restaurant_metrics(
            restaurant_id=restaurant_id,
            action="category_created",
        )

        logger.info(
            "category_created_successfully",
            extra={
                "category_id": category.id,
                "restaurant_id": restaurant_id,
            },
        )

        return CategoryResponse.model_validate(category)

    # ==============================================
    # UPDATE CATEGORY
    # ==============================================

    async def update_category(
        self,
        *,
        category_id: int,
        update_data: CategoryUpdate,
    ) -> CategoryResponse:
        """
        ØªØ­Ø¯ÙŠØ« ØªØµÙ†ÙŠÙ.

        Args:
            category_id: Ù…Ø¹Ø±Ù Ø§Ù„ØªØµÙ†ÙŠÙ
            update_data: Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„ØªØ­Ø¯ÙŠØ«

        Returns:
            CategoryResponse: Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„ØªØµÙ†ÙŠÙ Ø§Ù„Ù…Ø­Ø¯Ø«

        Raises:
            NotFoundError: Ø¥Ø°Ø§ Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø§Ù„ØªØµÙ†ÙŠÙ
            ConflictError: Ø¥Ø°Ø§ ÙƒØ§Ù† Ø§Ù„Ø§Ø³Ù… Ù…ÙƒØ±Ø±Ø§Ù‹
        """
        logger.info(
            "category_service_update",
            extra={
                "category_id": category_id,
                "update_fields": list(
                    update_data.model_dump(exclude_unset=True).keys()
                ),
            },
        )

        # 1ï¸âƒ£ Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† ÙˆØ¬ÙˆØ¯ Ø§Ù„ØªØµÙ†ÙŠÙ
        category = await self.repo.get_by_id(id=category_id)

        if not category:
            raise NotFoundError(
                message=f"Ø§Ù„ØªØµÙ†ÙŠÙ Ø¨Ù€ ID '{category_id}' ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯",
            )

        # 2ï¸âƒ£ ØªØ­Ø¶ÙŠØ± Ø¨ÙŠØ§Ù†Ø§Øª Ø§Ù„ØªØ­Ø¯ÙŠØ«
        updates = update_data.model_dump(exclude_unset=True)

        # 3ï¸âƒ£ ØªÙ†Ø¸ÙŠÙ Ø§Ù„Ø§Ø³Ù… Ø¥Ø°Ø§ ØªÙ… ØªØºÙŠÙŠØ±Ù‡
        if "name" in updates:
            updates["name"] = sanitize_input(updates["name"])

            existing = await self.repo.get_by_name(
                restaurant_id=category.restaurant_id,
                name=updates["name"],
            )

            if existing and existing.id != category_id:
                raise ConflictError(
                    message=(
                        f"ÙŠÙˆØ¬Ø¯ ØªØµÙ†ÙŠÙ Ø¨Ø§Ø³Ù… '{updates['name']}' "
                        f"Ø¨Ø§Ù„ÙØ¹Ù„ Ù„Ù‡Ø°Ø§ Ø§Ù„Ù…Ø·Ø¹Ù…"
                    ),
                )

        # 4ï¸âƒ£ ØªØ­Ø¯ÙŠØ« Ø§Ù„ØªØµÙ†ÙŠÙ
        updated = await self.repo.update(
            id=category_id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"Ø§Ù„ØªØµÙ†ÙŠÙ Ø¨Ù€ ID '{category_id}' ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯",
            )

        logger.info(
            "category_updated_successfully",
            extra={
                "category_id": category_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return CategoryResponse.model_validate(updated)

    # ==============================================
    # DELETE CATEGORY
    # ==============================================

    async def delete_category(
        self,
        *,
        category_id: int,
    ) -> None:
        """
        Ø­Ø°Ù ØªØµÙ†ÙŠÙ.

        Args:
            category_id: Ù…Ø¹Ø±Ù Ø§Ù„ØªØµÙ†ÙŠÙ

        Raises:
            NotFoundError: Ø¥Ø°Ø§ Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ Ø§Ù„ØªØµÙ†ÙŠÙ
            ValidationError: Ø¥Ø°Ø§ ÙƒØ§Ù† Ø§Ù„ØªØµÙ†ÙŠÙ ÙŠØ­ØªÙˆÙŠ Ø¹Ù„Ù‰ Ù…Ù†ØªØ¬Ø§Øª
        """
        logger.info(
            "category_service_delete",
            extra={"category_id": category_id},
        )

        category = await self.repo.get_by_id(id=category_id)

        if not category:
            raise NotFoundError(
                message=f"Ø§Ù„ØªØµÙ†ÙŠÙ Ø¨Ù€ ID '{category_id}' ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯",
            )

        restaurant_id = category.restaurant_id

        # 1ï¸âƒ£ Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù† Ø¹Ø¯Ù… ÙˆØ¬ÙˆØ¯ Ù…Ù†ØªØ¬Ø§Øª
        product_count = await self._count_products_in_category(
            category_id=category_id,
        )

        if product_count > 0:
            raise ValidationError(
                message="Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø­Ø°Ù Ø§Ù„ØªØµÙ†ÙŠÙ Ù„Ø£Ù†Ù‡ ÙŠØ­ØªÙˆÙŠ Ø¹Ù„Ù‰ Ù…Ù†ØªØ¬Ø§Øª",
                details={
                    "category_id": category_id,
                    "product_count": product_count,
                },
            )

        # 2ï¸âƒ£ Ø­Ø°Ù Ø§Ù„ØªØµÙ†ÙŠÙ
        await self.repo.delete(id=category_id)

        # 3ï¸âƒ£ ØªØ­Ø¯ÙŠØ« Ù…Ù‚Ø§ÙŠÙŠØ³ Ø§Ù„Ù…Ø·Ø¹Ù…
        await self._update_restaurant_metrics(
            restaurant_id=restaurant_id,
            action="category_deleted",
        )

        # 4ï¸âƒ£ ØªÙ‚Ù„ÙŠÙ„ Ø¹Ø¯Ø§Ø¯ Ø§Ø³ØªØ®Ø¯Ø§Ù… Ø§Ù„Ù…ÙŠØ²Ø© (Ù…Ø¹ session)
        feature_id = await self._get_category_feature_id(restaurant_id=restaurant_id)
        if feature_id is not None:
            await decrease_usage(
                session=self.session,
                restaurant_id=restaurant_id,
                feature_id=feature_id,
            )

        logger.info(
            "category_deleted_successfully",
            extra={
                "category_id": category_id,
                "restaurant_id": restaurant_id,
            },
        )

    # ==============================================
    # REORDER CATEGORIES
    # ==============================================

    async def reorder_categories(
        self,
        *,
        restaurant_id: int,
        category_order: list[int],
    ) -> None:
        """
        Ø¥Ø¹Ø§Ø¯Ø© ØªØ±ØªÙŠØ¨ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª.

        Args:
            restaurant_id: Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø·Ø¹Ù…
            category_order: Ù‚Ø§Ø¦Ù…Ø© Ù…Ø¹Ø±ÙØ§Øª Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª Ø¨Ø§Ù„ØªØ±ØªÙŠØ¨ Ø§Ù„Ø¬Ø¯ÙŠØ¯

        Raises:
            NotFoundError: Ø¥Ø°Ø§ ÙƒØ§Ù† Ø£Ø­Ø¯ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯
            ValidationError: Ø¥Ø°Ø§ ÙƒØ§Ù†Øª Ø§Ù„Ù‚Ø§Ø¦Ù…Ø© ÙØ§Ø±ØºØ© Ø£Ùˆ ØªØ­ØªÙˆÙŠ Ø¹Ù„Ù‰ Ù…Ø¹Ø±ÙØ§Øª Ù…ÙƒØ±Ø±Ø©
        """
        logger.info(
            "category_service_reorder",
            extra={
                "restaurant_id": restaurant_id,
                "category_count": len(category_order),
            },
        )

        if not category_order:
            raise ValidationError(
                message="Ù‚Ø§Ø¦Ù…Ø© ØªØ±ØªÙŠØ¨ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø£Ù† ØªÙƒÙˆÙ† ÙØ§Ø±ØºØ©",
            )

        if len(category_order) != len(set(category_order)):
            raise ValidationError(
                message="Ù‚Ø§Ø¦Ù…Ø© ØªØ±ØªÙŠØ¨ Ø§Ù„ØªØµÙ†ÙŠÙØ§Øª ØªØ­ØªÙˆÙŠ Ø¹Ù„Ù‰ Ù…Ø¹Ø±ÙØ§Øª Ù…ÙƒØ±Ø±Ø©",
            )

        for index, category_id in enumerate(category_order):
            category = await self.repo.get_by_id(id=category_id)

            if not category:
                raise NotFoundError(
                    message=f"Ø§Ù„ØªØµÙ†ÙŠÙ Ø¨Ù€ ID '{category_id}' ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯",
                )

            if category.restaurant_id != restaurant_id:
                raise ValidationError(
                    message=f"Ø§Ù„ØªØµÙ†ÙŠÙ '{category_id}' Ù„Ø§ ÙŠÙ†ØªÙ…ÙŠ Ù„Ù‡Ø°Ø§ Ø§Ù„Ù…Ø·Ø¹Ù…",
                )

            await self.repo.update(
                id=category_id,
                data={"sort_order": index},
            )

        logger.info(
            "categories_reordered_successfully",
            extra={
                "restaurant_id": restaurant_id,
                "category_count": len(category_order),
            },
        )

    # ==========================================
    # ðŸ› ï¸ PRIVATE HELPERS
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
        ØªØ­Ø¯ÙŠØ« Ù…Ù‚Ø§ÙŠÙŠØ³ Ø§Ù„Ù…Ø·Ø¹Ù….

        âœ… Ù†Ø³ØªØ®Ø¯Ù… RestaurantMetricsRepository
        âœ… Ù†Ø³ØªØ®Ø¯Ù… increment/decrement Ø¨Ø¯Ù„Ø§Ù‹ Ù…Ù† update Ø§Ù„ÙŠØ¯ÙˆÙŠ

        Args:
            restaurant_id: Ù…Ø¹Ø±Ù Ø§Ù„Ù…Ø·Ø¹Ù…
            action: Ù†ÙˆØ¹ Ø§Ù„Ø¥Ø¬Ø±Ø§Ø¡ (category_created, category_deleted)
        """
        try:
            if action == "category_created":
                await self.metrics_repo.increment_categories_count(
                    restaurant_id=restaurant_id,
                    amount=1,
                )
            elif action == "category_deleted":
                await self.metrics_repo.decrement_categories_count(
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

__all__ = [
    "CATEGORY_FEATURE_CODE",
    "MAX_CATEGORIES_PER_RESTAURANT",
    "CategoryData",
    "CategoryList",
    "CategoryService",
]
