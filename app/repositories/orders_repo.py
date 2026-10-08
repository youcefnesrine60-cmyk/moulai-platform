from sqlalchemy.orm import raiseload, selectinload
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
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    and_,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.order import Order
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OrderData = Dict[str, Any]
OrderUpdateData = Dict[str, Any]
OrderList = List[Order]

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
        self.query_options = [raiseload("*"), selectinload(Order.payments).raiseload("*"), selectinload(Order.user).raiseload("*")]

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ORDER NUMBER
    # ==============================================

    async def get_with_relations(self, *, order_id):
        from app.models.order_item import OrderItem
        return (await self.session.execute(self._select().where(Order.id == order_id).options(
            selectinload(Order.items).raiseload("*"),
            selectinload(Order.items).selectinload(OrderItem.options).raiseload("*"),
            selectinload(Order.status_history).raiseload("*"),
        ))).scalar_one_or_none()

    async def get_by_order_number(
        self,
        *,
        restaurant_id: int,
        order_number: str,
    ) -> Optional[Order]:
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
                self._select()
                .where(
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
        status: Optional[str] = None,
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

            query = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)

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
        restaurant_id: Optional[int] = None,
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

            query = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)

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
        restaurant_id: Optional[int] = None,
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

            query = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)

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
        restaurant_id: Optional[int] = None,
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
    ) -> Optional[Order]:
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
    ) -> Optional[Order]:
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
        status: Optional[str] = "completed",
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
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ORDER (COMPATIBILITY)
# ==============================================

async def create_order(
    *,
    restaurant_id: int,
    branch_id: Optional[int],
    table_id: Optional[int],
    employee_id: Optional[int],
    order_number: str,
    order_type: str,
    customer_name: Optional[str],
    customer_phone: Optional[str],
    delivery_address: Optional[str],
    customer_note: Optional[str],
    status: str,
    subtotal_amount: float,
    discount_amount: float,
    tax_amount: float,
    delivery_amount: float,
    total_amount: float,
    session: AsyncSession,
) -> int:
    """
    إنشاء طلب جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        branch_id: معرف الفرع
        table_id: معرف الطاولة
        employee_id: معرف الموظف
        order_number: رقم الطلب
        order_type: نوع الطلب
        customer_name: اسم العميل
        customer_phone: رقم هاتف العميل
        delivery_address: عنوان التوصيل
        customer_note: ملاحظات العميل
        status: حالة الطلب
        subtotal_amount: المبلغ الإجمالي قبل الخصم
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المبلغ النهائي
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        معرف الطلب
    """
    repo = OrdersRepository(session=session)

    data: OrderData = {
        "restaurant_id": restaurant_id,
        "branch_id": branch_id,
        "table_id": table_id,
        "employee_id": employee_id,
        "order_number": order_number,
        "order_type": order_type,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "delivery_address": delivery_address,
        "customer_note": customer_note,
        "status": status,
        "subtotal_amount": subtotal_amount,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "delivery_amount": delivery_amount,
        "total_amount": total_amount,
    }

    order = await repo.create(data=data)

    logger.info(
        "order_created",
        extra={
            "order_id": order.id,
            "restaurant_id": restaurant_id,
        },
    )

    return order.id


# ==============================================
# GET ORDER (COMPATIBILITY)
# ==============================================

async def get_order(
    *,
    order_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على طلب بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات الطلب أو None
    """
    repo = OrdersRepository(session=session)

    order = await repo.get_by_id(id=order_id)

    if not order:
        return None

    return {
        "id": order.id,
        "restaurant_id": order.restaurant_id,
        "branch_id": order.branch_id,
        "table_id": order.table_id,
        "employee_id": order.employee_id,
        "order_number": order.order_number,
        "order_type": order.order_type,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "delivery_address": order.delivery_address,
        "customer_note": order.customer_note,
        "status": order.status,
        "subtotal_amount": order.subtotal_amount,
        "discount_amount": order.discount_amount,
        "tax_amount": order.tax_amount,
        "delivery_amount": order.delivery_amount,
        "total_amount": order.total_amount,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


# ==============================================
# GET ORDER BY NUMBER (COMPATIBILITY)
# ==============================================

async def get_order_by_number(
    *,
    restaurant_id: int,
    order_number: str,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على طلب بواسطة رقم الطلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        order_number: رقم الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات الطلب أو None
    """
    repo = OrdersRepository(session=session)

    order = await repo.get_by_order_number(
        restaurant_id=restaurant_id,
        order_number=order_number,
    )

    if not order:
        return None

    return {
        "id": order.id,
        "restaurant_id": order.restaurant_id,
        "branch_id": order.branch_id,
        "table_id": order.table_id,
        "employee_id": order.employee_id,
        "order_number": order.order_number,
        "order_type": order.order_type,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "delivery_address": order.delivery_address,
        "customer_note": order.customer_note,
        "status": order.status,
        "subtotal_amount": order.subtotal_amount,
        "discount_amount": order.discount_amount,
        "tax_amount": order.tax_amount,
        "delivery_amount": order.delivery_amount,
        "total_amount": order.total_amount,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


# ==============================================
# GET RESTAURANT ORDERS (COMPATIBILITY)
# ==============================================

async def get_restaurant_orders(
    *,
    restaurant_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    الحصول على طلبات مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        status: حالة الطلب (اختياري)
        
    Returns:
        قائمة الطلبات
    """
    repo = OrdersRepository(session=session)

    orders = await repo.get_by_restaurant_id(
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
        status=status,
    )

    result = []

    for order in orders:
        result.append({
            "id": order.id,
            "restaurant_id": order.restaurant_id,
            "branch_id": order.branch_id,
            "table_id": order.table_id,
            "employee_id": order.employee_id,
            "order_number": order.order_number,
            "order_type": order.order_type,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "customer_note": order.customer_note,
            "status": order.status,
            "subtotal_amount": order.subtotal_amount,
            "discount_amount": order.discount_amount,
            "tax_amount": order.tax_amount,
            "delivery_amount": order.delivery_amount,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        })

    return result


# ==============================================
# GET ORDERS BY STATUS (COMPATIBILITY)
# ==============================================

async def get_orders_by_status(
    *,
    restaurant_id: int,
    status: str,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على طلبات حسب الحالة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        status: حالة الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        قائمة الطلبات
    """
    repo = OrdersRepository(session=session)

    orders = await repo.get_by_status(
        status=status,
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for order in orders:
        result.append({
            "id": order.id,
            "restaurant_id": order.restaurant_id,
            "branch_id": order.branch_id,
            "table_id": order.table_id,
            "employee_id": order.employee_id,
            "order_number": order.order_number,
            "order_type": order.order_type,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "customer_note": order.customer_note,
            "status": order.status,
            "subtotal_amount": order.subtotal_amount,
            "discount_amount": order.discount_amount,
            "tax_amount": order.tax_amount,
            "delivery_amount": order.delivery_amount,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        })

    return result


# ==============================================
# UPDATE ORDER STATUS (COMPATIBILITY)
# ==============================================

async def update_order_status(
    *,
    order_id: int,
    status: str,
    session: AsyncSession,
) -> None:
    """
    تحديث حالة الطلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        status: الحالة الجديدة
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrdersRepository(session=session)

    await repo.update_status(
        order_id=order_id,
        status=status,
    )


# ==============================================
# UPDATE ORDER TOTALS (COMPATIBILITY)
# ==============================================

async def update_order_totals(
    *,
    order_id: int,
    subtotal_amount: float,
    discount_amount: float,
    tax_amount: float,
    delivery_amount: float,
    total_amount: float,
    session: AsyncSession,
) -> None:
    """
    تحديث مبالغ الطلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        subtotal_amount: المبلغ الإجمالي قبل الخصم
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المبلغ النهائي
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrdersRepository(session=session)

    await repo.update_totals(
        order_id=order_id,
        subtotal_amount=subtotal_amount,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        delivery_amount=delivery_amount,
        total_amount=total_amount,
    )


# ==============================================
# DELETE ORDER (COMPATIBILITY)
# ==============================================

async def delete_order(
    *,
    order_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف طلب (دالة متوافقة مع الإصدار القديم).
    
    Args:
        order_id: معرف الطلب
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    repo = OrdersRepository(session=session)

    await repo.delete(id=order_id)

    logger.info(
        "order_deleted",
        extra={"order_id": order_id},
    )

# ==============================================
# 🔄 TRANSACTION FUNCTIONS (للتوافق مع الكود القديم)
# دوال معاملات متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE ORDER TX
# ==============================================

async def create_order_tx(
    *,
    conn: AsyncSession,
    restaurant_id: int,
    branch_id: Optional[int],
    table_id: Optional[int],
    employee_id: Optional[int],
    order_number: str,
    order_type: str,
    customer_name: Optional[str],
    customer_phone: Optional[str],
    delivery_address: Optional[str],
    customer_note: Optional[str],
    status: str,
    subtotal_amount: float,
    discount_amount: float,
    tax_amount: float,
    delivery_amount: float,
    total_amount: float,
) -> int:
    """
    إنشاء طلب جديد (معاملة) - دالة متوافقة مع الإصدار القديم.
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        restaurant_id: معرف المطعم
        branch_id: معرف الفرع
        table_id: معرف الطاولة
        employee_id: معرف الموظف
        order_number: رقم الطلب
        order_type: نوع الطلب
        customer_name: اسم العميل
        customer_phone: رقم هاتف العميل
        delivery_address: عنوان التوصيل
        customer_note: ملاحظات العميل
        status: حالة الطلب
        subtotal_amount: المبلغ الإجمالي قبل الخصم
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المبلغ النهائي
        
    Returns:
        معرف الطلب
    """
    repo = OrdersRepository(conn)

    data = {
        "restaurant_id": restaurant_id,
        "branch_id": branch_id,
        "table_id": table_id,
        "employee_id": employee_id,
        "order_number": order_number,
        "order_type": order_type,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "delivery_address": delivery_address,
        "customer_note": customer_note,
        "status": status,
        "subtotal_amount": subtotal_amount,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "delivery_amount": delivery_amount,
        "total_amount": total_amount,
    }

    order = await repo.create(data=data)

    logger.info(
        "order_created_tx",
        extra={
            "order_id": order.id,
            "restaurant_id": restaurant_id,
        },
    )

    return order.id


# ==============================================
# UPDATE ORDER TOTALS TX
# ==============================================

async def update_order_totals_tx(
    *,
    conn: AsyncSession,
    order_id: int,
    subtotal_amount: float,
    discount_amount: float,
    tax_amount: float,
    delivery_amount: float,
    total_amount: float,
) -> None:
    """
    تحديث مبالغ الطلب (معاملة) - دالة متوافقة مع الإصدار القديم.
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        order_id: معرف الطلب
        subtotal_amount: المبلغ الإجمالي قبل الخصم
        discount_amount: مبلغ الخصم
        tax_amount: مبلغ الضريبة
        delivery_amount: مبلغ التوصيل
        total_amount: المبلغ النهائي
    """
    repo = OrdersRepository(conn)

    await repo.update_totals(
        order_id=order_id,
        subtotal_amount=subtotal_amount,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        delivery_amount=delivery_amount,
        total_amount=total_amount,
    )


# ==============================================
# UPDATE ORDER STATUS TX
# ==============================================

async def update_order_status_tx(
    *,
    conn: AsyncSession,
    order_id: int,
    status: str,
) -> None:
    """
    تحديث حالة الطلب (معاملة) - دالة متوافقة مع الإصدار القديم.
    
    Args:
        conn: جلسة قاعدة البيانات (AsyncSession)
        order_id: معرف الطلب
        status: الحالة الجديدة
    """
    repo = OrdersRepository(conn)

    await repo.update_status(
        order_id=order_id,
        status=status,
    )

async def lock_order(*, order_id, session):
    """Lock the aggregate before checking rules or mutating its children."""
    return (await session.execute(OrdersRepository(session=session)._select().where(Order.id == order_id)
                                  .with_for_update(of=Order).execution_options(populate_existing=True))).scalar_one_or_none()
