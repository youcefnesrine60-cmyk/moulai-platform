from app.services.business.orders.transaction import transactional_order
# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 📦 ORDER SERVICE
# واجهة موحدة لخدمات الطلبات
# ==============================================

from typing import (
    Optional,
    Tuple,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
)

from app.models.order import Order
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    OrderStatusUpdate,
    OrderListResponse,
    OrderSummary,
)

# ✅ استيراد دوال الخدمة من مجلد orders
from app.services.business.orders import (

    # Create
    create_restaurant_order,
    create_order_with_items,

    # Read
    get_restaurant_order,
    get_orders,
    get_orders_by_status,
    get_order_with_details,
    count_orders_by_restaurant,

    # Update
    change_order_status,
    recalculate_order_totals,
    update_order,

    # Delete
    remove_order,

    # Complete
    complete_order,

    # Cancel
    cancel_order,

    # Paid
    mark_order_paid,

    # Constants
    ALLOWED_TRANSITIONS,

)


# ==============================================
# 📦 ORDER SERVICE CLASS
# ==============================================

class OrderService:
    """
    خدمة الطلبات - واجهة موحدة لجميع عمليات الطلبات.
    
    توفر هذه الخدمة واجهة مبسطة للتعامل مع الطلبات，
    حيث تقوم بتجميع جميع دوال الخدمة من مجلد orders/.
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة الطلبات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        order_id: int,
    ) -> OrderResponse:
        """
        الحصول على طلب بالمعرف.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            OrderResponse: بيانات الطلب
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
        """
        order = await get_restaurant_order(
            order_id=order_id,
            session=self.session,
        )

        if not order:
            raise NotFoundError(
                message=f"الطلب بـ ID '{order_id}' غير موجود",
            )

        return OrderResponse.model_validate(order)

    # ==============================================
    # GET WITH DETAILS
    # ==============================================

    async def get_with_details(
        self,
        *,
        order_id: int,
    ) -> Order:
        """
        الحصول على طلب مع جميع علاقاته.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            Order: كائن الطلب مع العلاقات
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
        """
        order = await get_order_with_details(
            order_id=order_id,
            session=self.session,
        )

        if not order:
            raise NotFoundError(
                message=f"الطلب بـ ID '{order_id}' غير موجود",
            )

        return order

    # ==============================================
    # GET BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderListResponse:
        """
        الحصول على طلبات مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            OrderListResponse: قائمة الطلبات مع الإحصائيات
        """
        orders = await get_orders(
            restaurant_id=restaurant_id,
            session=self.session,
            skip=skip,
            limit=limit,
        )

        total = await count_orders_by_restaurant(
            restaurant_id=restaurant_id,
            session=self.session,
        )

        return OrderListResponse(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # GET BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        restaurant_id: int,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> OrderListResponse:
        """
        الحصول على طلبات مطعم حسب الحالة.
        
        Args:
            restaurant_id: معرف المطعم
            status: حالة الطلب
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            OrderListResponse: قائمة الطلبات مع الإحصائيات
            
        Raises:
            ValidationError: إذا كانت الحالة غير صالحة
        """
        if status not in ALLOWED_TRANSITIONS:
            raise ValidationError(
                message=f"الحالة '{status}' غير صالحة",
                details={
                    "status": status,
                    "valid_statuses": list(ALLOWED_TRANSITIONS.keys()),
                },
            )

        orders = await get_orders_by_status(
            restaurant_id=restaurant_id,
            status=status,
            session=self.session,
            skip=skip,
            limit=limit,
        )

        total = await count_orders_by_restaurant(
            restaurant_id=restaurant_id,
            session=self.session,
            status=status,
        )

        return OrderListResponse(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE ORDER
    # ==============================================

    @transactional_order
    async def create_order(
        self,
        *,
        order_data: OrderCreate,
    ) -> OrderResponse:
        """
        إنشاء طلب جديد.
        
        Args:
            order_data: بيانات الطلب
            
        Returns:
            OrderResponse: الطلب المنشأ
            
        Raises:
            ValidationError: إذا كانت البيانات غير صالحة
        """
        values = order_data.model_dump(exclude={"items"})
        if order_data.items:
            order_id = await create_order_with_items(
                **values, items=[item.model_dump() for item in order_data.items],
                session=self.session,
            )
        else:
            order_id = await create_restaurant_order(
                **values, order_number="", session=self.session,
            )

        order = await get_restaurant_order(
            order_id=order_id,
            session=self.session,
        )

        return OrderResponse.model_validate(order)

    # ==============================================
    # UPDATE ORDER
    # ==============================================

    @transactional_order
    async def update_order(
        self,
        *,
        order_id: int,
        update_data: OrderUpdate,
    ) -> OrderResponse:
        """
        تحديث طلب موجود.
        
        Args:
            order_id: معرف الطلب
            update_data: بيانات التحديث
            
        Returns:
            OrderResponse: الطلب المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كان الطلب مقفلاً
        """
        updates = update_data.model_dump(exclude_unset=True)

        # منع تحديث الحالة عبر هذه الدالة
        if "status" in updates:
            del updates["status"]

        updated_order = await update_order(
            order_id=order_id,
            data=updates,
            session=self.session,
        )

        return OrderResponse.model_validate(updated_order)

    # ==============================================
    # UPDATE ORDER STATUS
    # ==============================================

    @transactional_order
    async def update_order_status(
        self,
        *,
        order_id: int,
        status_data: OrderStatusUpdate,
    ) -> OrderResponse:
        """
        تحديث حالة الطلب.
        
        Args:
            order_id: معرف الطلب
            status_data: بيانات تحديث الحالة
            
        Returns:
            OrderResponse: الطلب المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كان الانتقال غير مسموح
        """
        updated_order = await change_order_status(
            order_id=order_id,
            new_status=status_data.status,
            employee_id=status_data.employee_id,
            note=status_data.note,
            session=self.session,
        )

        return OrderResponse.model_validate(updated_order)

    # ==============================================
    # COMPLETE ORDER
    # ==============================================

    @transactional_order
    async def complete_order(
        self,
        *,
        order_id: int,
        employee_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> OrderResponse:
        """
        إكمال الطلب.
        
        Args:
            order_id: معرف الطلب
            employee_id: معرف الموظف (اختياري)
            note: ملاحظة (اختياري)
            
        Returns:
            OrderResponse: الطلب المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كانت الحالة لا تسمح بالإكمال
        """
        await complete_order(
            order_id=order_id,
            employee_id=employee_id,
            note=note,
            session=self.session,
        )

        order = await get_restaurant_order(
            order_id=order_id,
            session=self.session,
        )

        return OrderResponse.model_validate(order)

    # ==============================================
    # CANCEL ORDER
    # ==============================================

    @transactional_order
    async def cancel_order(
        self,
        *,
        order_id: int,
        employee_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> OrderResponse:
        """
        إلغاء الطلب.
        
        Args:
            order_id: معرف الطلب
            employee_id: معرف الموظف (اختياري)
            reason: سبب الإلغاء (اختياري)
            
        Returns:
            OrderResponse: الطلب المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كانت الحالة لا تسمح بالإلغاء
        """
        await cancel_order(
            order_id=order_id,
            employee_id=employee_id,
            reason=reason,
            session=self.session,
        )

        order = await get_restaurant_order(
            order_id=order_id,
            session=self.session,
        )

        return OrderResponse.model_validate(order)

    # ==============================================
    # MARK AS PAID
    # ==============================================

    @transactional_order
    async def mark_as_paid(
        self,
        *,
        order_id: int,
        payment_id: int,
    ) -> OrderResponse:
        """
        تحديد الطلب كمدفوع.
        
        Args:
            order_id: معرف الطلب
            payment_id: معرف الدفعة
            
        Returns:
            OrderResponse: الطلب المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب أو الدفعة
            ValidationError: إذا كانت الدفعة لا تخص الطلب
        """
        await mark_order_paid(
            order_id=order_id,
            payment_id=payment_id,
            session=self.session,
        )

        order = await get_restaurant_order(
            order_id=order_id,
            session=self.session,
        )

        return OrderResponse.model_validate(order)

    # ==============================================
    # DELETE ORDER
    # ==============================================

    @transactional_order
    async def delete_order(
        self,
        *,
        order_id: int,
        permanent: bool = False,
    ) -> None:
        """
        حذف طلب.
        
        Args:
            order_id: معرف الطلب
            permanent: حذف نهائي
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كان الطلب مقفلاً أو مدفوعاً
        """
        await remove_order(
            order_id=order_id,
            permanent=permanent,
            session=self.session,
        )

    # ==============================================
    # RECALCULATE ORDER TOTAL
    # ==============================================

    @transactional_order
    async def recalculate_order_total(
        self,
        *,
        order_id: int,
    ) -> Tuple[float, float, float, float, float]:
        """
        إعادة حساب إجمالي الطلب.
        
        Args:
            order_id: معرف الطلب
            
        Returns:
            Tuple[float, float, float, float, float]: (subtotal, discount, tax, delivery, total)
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
        """
        return await recalculate_order_totals(
            order_id=order_id,
            session=self.session,
        )

    # ==============================================
    # GET ORDER SUMMARY
    # ==============================================

    async def get_order_summary(
        self,
        *,
        restaurant_id: int,
    ) -> OrderSummary:
        """
        الحصول على ملخص الطلبات لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            OrderSummary: ملخص الطلبات
        """
        orders = await get_orders(
            restaurant_id=restaurant_id,
            session=self.session,
            limit=10000,
        )

        status_counts = {}
        total_revenue = 0.0

        for order in orders:
            status = order.status
            status_counts[status] = status_counts.get(status, 0) + 1

            if order.status in ["completed", "delivered", "paid"]:
                total_revenue += order.total_amount

        total_orders = len(orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0

        return OrderSummary(
            total_orders=total_orders,
            pending_orders=status_counts.get("pending", 0),
            confirmed_orders=status_counts.get("confirmed", 0),
            preparing_orders=status_counts.get("preparing", 0),
            ready_orders=status_counts.get("ready", 0),
            delivering_orders=status_counts.get("delivering", 0),
            delivered_orders=status_counts.get("delivered", 0),
            completed_orders=status_counts.get("completed", 0),
            cancelled_orders=status_counts.get("cancelled", 0),
            total_revenue=round(total_revenue, 2),
            avg_order_value=round(avg_order_value, 2),
        )