# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / REPOSITORIES / ORDERS REPO
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for orders repo.

Part of MoulAI Platform - Agent-as-a-Service.
"""

# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================
# ==============================================
# 📦 ORDERS REPOSITORY
# عمليات قاعدة البيانات للطلبات باستخدام SQLAlchemy
# ==============================================
from typing import (
    Any,
)

from sqlalchemy import (
    and_,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import raiseload, selectinload

from app.core.logger import logger
from app.models.order import Order
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderData = dict[str, Any]
OrderUpdateData = dict[str, Any]
OrderList = list[Order]

# ==============================================
# 📦 ORDERS REPOSITORY
# ==============================================


class OrdersRepository(BaseRepository[Order, OrderData, OrderUpdateData]):
    """
    مستودع الطلبات - يوفر عمليات خاصة بالطلبات.

    مسؤول عن:
        - عمليات CRUD الأساسية للطلبات
        - البحث والتصفية حسب المطعم والفرع والحالة
        - تحديث حالة الطلب ومبالغه
        - إحصائيات الطلبات

    Attributes:
        model: نموذج Order
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    # ==============================================
    #   INIT
    # ==============================================

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع الطلبات.

        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(Order, session)
        self.commit_on_write = False
        self.query_options = [
            raiseload("*"),
            selectinload(Order.payments).raiseload("*"),
            selectinload(Order.user).raiseload("*"),
        ]

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ORDER NUMBER
    # ==============================================

    async def get_with_relations(self, *, order_id):
        from app.models.order_item import OrderItem

        return (
            await self.session.execute(
                self._select()
                .where(Order.id == order_id)
                .options(
                    selectinload(Order.items).raiseload("*"),
                    selectinload(Order.items)
                    .selectinload(OrderItem.options)
                    .raiseload("*"),
                    selectinload(Order.status_history).raiseload("*"),
                )
            )
        ).scalar_one_or_none()

    # ==============================================
    # GET BY ORDER NUMBER
    # ==============================================

    async def get_by_order_number(
        self,
        *,
        restaurant_id: int,
        order_number: str,
    ) -> Order | None:
        """
        الحصول على طلب بواسطة رقم الطلب.

        Args:
            restaurant_id: معرف المطعم
            order_number: رقم الطلب

        Returns:
            كائن Order أو None
        """
        try:
            result = await self.session.execute(
                self._select().where(
                    and_(
                        self.model.restaurant_id == restaurant_id,
                        self.model.order_number == order_number,
                    ),
                ),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "orders_repo_get_by_order_number_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "order_number": order_number,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY RESTAURANT ID
    # ==============================================

    async def get_by_restaurant_id(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> OrderList:
        """
        الحصول على طلبات مطعم معين.

        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            status: حالة الطلب (اختياري)

        Returns:
            قائمة الطلبات
        """
        try:
            query = self._select().where(
                self.model.restaurant_id == restaurant_id,
            )

            if status is not None:
                query = query.where(self.model.status == status)

            query = (
                query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "orders_repo_get_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        status: str,
        restaurant_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderList:
        """
        الحصول على طلبات حسب الحالة.

        Args:
            status: حالة الطلب
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الطلبات
        """
        try:
            query = self._select().where(self.model.status == status)

            if restaurant_id is not None:
                query = query.where(self.model.restaurant_id == restaurant_id)

            query = (
                query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "orders_repo_get_by_status_failed",
                extra={
                    "status": status,
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY BRANCH ID
    # ==============================================

    async def get_by_branch_id(
        self,
        *,
        branch_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderList:
        """
        الحصول على طلبات فرع معين.

        Args:
            branch_id: معرف الفرع
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الطلبات
        """
        try:
            query = (
                self._select()
                .where(self.model.branch_id == branch_id)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "orders_repo_get_by_branch_failed",
                extra={
                    "branch_id": branch_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY CUSTOMER
    # ==============================================

    async def get_by_customer(
        self,
        *,
        customer_phone: str,
        restaurant_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderList:
        """
        الحصول على طلبات عميل معين.

        Args:
            customer_phone: رقم هاتف العميل
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الطلبات
        """
        try:
            query = self._select().where(
                self.model.customer_phone == customer_phone,
            )

            if restaurant_id is not None:
                query = query.where(self.model.restaurant_id == restaurant_id)

            query = (
                query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "orders_repo_get_by_customer_failed",
                extra={
                    "customer_phone": customer_phone,
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise

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
    ) -> OrderList:
        """
        البحث عن طلبات.

        Args:
            query: نص البحث
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات

        Returns:
            قائمة الطلبات
        """
        try:
            conditions = [
                or_(
                    self.model.order_number.ilike(f"%{query}%"),
                    self.model.customer_name.ilike(f"%{query}%"),
                    self.model.customer_phone.ilike(f"%{query}%"),
                ),
            ]

            if restaurant_id is not None:
                conditions.append(
                    self.model.restaurant_id == restaurant_id,
                )

            stmt = (
                self._select()
                .where(*conditions)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "orders_repo_search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise

    # ==========================================
    # ✏️ UPDATES
    # ==========================================

    # ==============================================
    # UPDATE STATUS
    # ==============================================

    async def update_status(
        self,
        *,
        order_id: int,
        status: str,
    ) -> Order | None:
        """
        تحديث حالة الطلب.

        Args:
            order_id: معرف الطلب
            status: الحالة الجديدة

        Returns:
            كائن Order المحدث أو None
        """
        logger.info(
            "orders_repo_update_status",
            extra={
                "order_id": order_id,
                "status": status,
            },
        )

        return await self.update(
            id=order_id,
            data={"status": status},
        )

    # ==============================================
    # UPDATE TOTALS
    # ==============================================

    async def update_totals(
        self,
        *,
        order_id: int,
        subtotal_amount: float,
        discount_amount: float,
        tax_amount: float,
        delivery_amount: float,
        total_amount: float,
    ) -> Order | None:
        """
        تحديث مبالغ الطلب.

        Args:
            order_id: معرف الطلب
            subtotal_amount: المبلغ الإجمالي قبل الخصم
            discount_amount: مبلغ الخصم
            tax_amount: مبلغ الضريبة
            delivery_amount: مبلغ التوصيل
            total_amount: المبلغ النهائي

        Returns:
            كائن Order المحدث أو None
        """
        logger.info(
            "orders_repo_update_totals",
            extra={
                "order_id": order_id,
                "subtotal_amount": subtotal_amount,
                "total_amount": total_amount,
            },
        )

        data: OrderUpdateData = {
            "subtotal_amount": subtotal_amount,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "delivery_amount": delivery_amount,
            "total_amount": total_amount,
        }

        return await self.update(
            id=order_id,
            data=data,
        )

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY STATUS
    # ==============================================

    async def count_by_status(
        self,
        *,
        restaurant_id: int,
        status: str,
    ) -> int:
        """
        حساب عدد طلبات مطعم معين حسب الحالة.

        Args:
            restaurant_id: معرف المطعم
            status: حالة الطلب

        Returns:
            عدد الطلبات
        """
        return await self.count(
            filters={
                "restaurant_id": restaurant_id,
                "status": status,
            },
        )

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
    ) -> int:
        """
        حساب عدد طلبات مطعم معين.

        Args:
            restaurant_id: معرف المطعم

        Returns:
            عدد الطلبات
        """
        return await self.count(filters={"restaurant_id": restaurant_id})

    # ==============================================
    # TOTAL AMOUNT BY RESTAURANT
    # ==============================================

    async def total_amount_by_restaurant(
        self,
        *,
        restaurant_id: int,
        status: str | None = "completed",
    ) -> float:
        """
        حساب إجمالي مبلغ الطلبات لمطعم معين.

        Args:
            restaurant_id: معرف المطعم
            status: حالة الطلب (اختياري)

        Returns:
            إجمالي المبلغ
        """
        try:
            from sqlalchemy import func

            query = select(func.sum(self.model.total_amount)).where(
                self.model.restaurant_id == restaurant_id,
            )

            if status is not None:
                query = query.where(self.model.status == status)

            result = await self.session.execute(query)
            total = result.scalar_one()

            return float(total) if total else 0.0

        except Exception as e:
            logger.exception(
                "orders_repo_total_amount_by_restaurant_failed",
                extra={
                    "restaurant_id": restaurant_id,
                    "error": str(e),
                },
            )
            raise


# ==============================================
# LOCK ORDER
# ==============================================


async def lock_order(*, order_id, session):
    """Lock the aggregate before checking rules or mutating its children."""
    return (
        await session.execute(
            OrdersRepository(session=session)
            ._select()
            .where(Order.id == order_id)
            .with_for_update(of=Order)
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
