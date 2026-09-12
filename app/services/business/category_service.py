# ==============================================
# 📂 CATEGORY SERVICE
# Business Logic Layer
# منطق الأعمال للتصنيفات
#
# إنشاء تصنيف
# قراءة التصنيف
# قراءة تصنيفات المطعم
# حذف التصنيف
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession

# ✅ استيراد الاستثناءات
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

# ✅ استيراد دوال الأمان
from app.core.security import (
    sanitize_input,
)

from app.core.logger import logger
from app.models.category import Category
from app.models.restaurant_metric import RestaurantMetric
from app.repositories.base import BaseRepository
from app.repositories.categories_repo import CategoriesRepository
from app.services.business.feature_usage_counter_engine import (
    decrease_usage,
    increase_usage,
)

# ✅ استيراد المخططات
from app.schemas.categories import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CategoryListResponse,
    CategorySummary,
)


# ==============================================
# 🧩 CONSTANTS
# ==============================================

CATEGORY_FEATURE_ID = 2
MAX_CATEGORIES_PER_RESTAURANT = 20


# ==============================================
# 🧩 TYPES
# ==============================================

CategoryData = Dict[str, Any]
CategoryList = List[Category]


# ==============================================
# 📂 CATEGORY SERVICE
# ==============================================


class CategoryService:
    """
    خدمة التصنيفات - تدير منطق الأعمال للتصنيفات.
    
    مسؤولة عن:
        - إنشاء وإدارة التصنيفات
        - تحديث ترتيب التصنيفات
        - تحديث مقاييس المطعم
        - إدارة عداد استخدام الميزات
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع التصنيفات
        metrics_repo: مستودع مقاييس المطعم
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة التصنيفات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = CategoriesRepository(session)
        # استخدام BaseRepository مباشرة مع نموذج RestaurantMetric
        self.metrics_repo = BaseRepository(RestaurantMetric, session)

    # ==========================================
    # 📖 QUERIES
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
        الحصول على تصنيف بالمعرف.
        
        Args:
            category_id: معرف التصنيف
            
        Returns:
            CategoryResponse: بيانات التصنيف
            
        Raises:
            NotFoundError: إذا لم يتم العثور على التصنيف
        """
        logger.info(
            "category_service_get_by_id",
            extra={"category_id": category_id},
        )

        category = await self.repo.get_by_id(
            id=category_id,
        )

        if not category:
            raise NotFoundError(
                message=f"التصنيف بـ ID '{category_id}' غير موجود",
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
        الحصول على تصنيفات مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            CategoryListResponse: قائمة التصنيفات مع الإحصائيات
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
            items=[CategoryResponse.model_validate(category) for category in categories],
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
    ) -> Optional[Category]:
        """
        الحصول على تصنيف بواسطة اسمه.
        
        Args:
            restaurant_id: معرف المطعم
            name: اسم التصنيف
            
        Returns:
            كائن Category أو None
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
        restaurant_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> CategoryListResponse:
        """
        البحث عن تصنيفات.
        
        Args:
            query: نص البحث
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            CategoryListResponse: قائمة التصنيفات مع الإحصائيات
        """
        # تنظيف النص
        clean_query = sanitize_input(query)

        logger.info(
            "category_service_search",
            extra={
                "query": clean_query,
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
            items=[CategoryResponse.model_validate(category) for category in categories],
            total=total,
            skip=skip,
            limit=limit,
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
    ) -> int:
        """
        حساب عدد تصنيفات مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            int: عدد التصنيفات
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
        الحصول على ملخص التصنيفات لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            CategorySummary: ملخص التصنيفات
        """
        logger.info(
            "category_service_get_category_summary",
            extra={"restaurant_id": restaurant_id},
        )

        total = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

        # الحصول على التصنيفات مع عدد المنتجات لكل تصنيف
        categories = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            limit=1000,
        )

        categories_with_products = []

        for category in categories:
            # حساب عدد المنتجات في هذا التصنيف
            product_count = await self.repo.count_products_in_category(
                category_id=category.id,
            )
            categories_with_products.append({
                "id": category.id,
                "name": category.name,
                "product_count": product_count,
            })

        return CategorySummary(
            total_categories=total,
            categories=categories_with_products,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE CATEGORY
    # ==============================================

    async def create_category(
        self,
        *,
        restaurant_id: int,
        category_data: CategoryCreate,
        skip_feature_check: bool = False,
    ) -> CategoryResponse:
        """
        إنشاء تصنيف جديد.
        
        Args:
            restaurant_id: معرف المطعم
            category_data: بيانات التصنيف
            skip_feature_check: تخطي التحقق من الميزة (للاستخدام الداخلي)
            
        Returns:
            CategoryResponse: بيانات التصنيف المنشأ
            
        Raises:
            ConflictError: إذا كان الاسم موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صحيحة
            BranchLimitExceededError: إذا تجاوز المطعم الحد الأقصى للتصنيفات
        """
        # تنظيف الاسم
        name = sanitize_input(category_data.name)

        logger.info(
            "category_service_create",
            extra={
                "restaurant_id": restaurant_id,
                "category_name": name,
            },
        )

        # التحقق من الحد الأقصى للتصنيفات
        current_count = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

        if current_count >= MAX_CATEGORIES_PER_RESTAURANT:
            raise ValidationError(
                message=f"تجاوزت الحد الأقصى للتصنيفات ({MAX_CATEGORIES_PER_RESTAURANT})",
                details={
                    "restaurant_id": restaurant_id,
                    "current_count": current_count,
                    "max_allowed": MAX_CATEGORIES_PER_RESTAURANT,
                },
            )

        # التحقق من الميزة (Feature Guard)
        # TODO: إعادة تفعيل require_feature بعد اكتمال النظام
        # if not skip_feature_check:
        #     await require_feature(
        #         restaurant_id=restaurant_id,
        #         feature_id=CATEGORY_FEATURE_ID,
        #     )

        # التحقق من عدم وجود تصنيف بنفس الاسم للمطعم
        existing = await self.repo.get_by_name(
            restaurant_id=restaurant_id,
            name=name,
        )

        if existing:
            raise ConflictError(
                message=f"يوجد تصنيف باسم '{name}' بالفعل لهذا المطعم",
            )

        # إنشاء التصنيف
        data: CategoryData = {
            "restaurant_id": restaurant_id,
            "name": name,
            "sort_order": category_data.sort_order or 0,
        }

        category = await self.repo.create(data=data)

        # زيادة عداد استخدام الميزة
        await increase_usage(
            restaurant_id=restaurant_id,
            feature_id=CATEGORY_FEATURE_ID,
        )

        # تحديث مقاييس المطعم
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
        تحديث تصنيف.
        
        Args:
            category_id: معرف التصنيف
            update_data: بيانات التحديث
            
        Returns:
            CategoryResponse: بيانات التصنيف المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على التصنيف
            ConflictError: إذا كان الاسم موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صحيحة
        """
        logger.info(
            "category_service_update",
            extra={
                "category_id": category_id,
                "update_data": update_data.model_dump(exclude_unset=True),
            },
        )

        # التحقق من وجود التصنيف
        category = await self.repo.get_by_id(id=category_id)

        if not category:
            raise NotFoundError(
                message=f"التصنيف بـ ID '{category_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف الاسم إذا تم تغييره
        if "name" in updates:
            updates["name"] = sanitize_input(updates["name"])

            # التحقق من عدم وجود اسم مكرر
            existing = await self.repo.get_by_name(
                restaurant_id=category.restaurant_id,
                name=updates["name"],
            )

            if existing and existing.id != category_id:
                raise ConflictError(
                    message=f"يوجد تصنيف باسم '{updates['name']}' بالفعل لهذا المطعم",
                )

        # تحديث التصنيف
        updated = await self.repo.update(
            id=category_id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"التصنيف بـ ID '{category_id}' غير موجود",
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
        حذف تصنيف.
        
        Args:
            category_id: معرف التصنيف
            
        Raises:
            NotFoundError: إذا لم يتم العثور على التصنيف
            ValidationError: إذا كان التصنيف يحتوي على منتجات
        """
        logger.info(
            "category_service_delete",
            extra={"category_id": category_id},
        )

        category = await self.repo.get_by_id(id=category_id)

        if not category:
            raise NotFoundError(
                message=f"التصنيف بـ ID '{category_id}' غير موجود",
            )

        restaurant_id = category.restaurant_id

        # التحقق من عدم وجود منتجات في هذا التصنيف
        product_count = await self.repo.count_products_in_category(
            category_id=category_id,
        )

        if product_count > 0:
            raise ValidationError(
                message="لا يمكن حذف التصنيف لأنه يحتوي على منتجات",
                details={
                    "category_id": category_id,
                    "product_count": product_count,
                },
            )

        # حذف التصنيف
        await self.repo.delete(id=category_id)

        # تحديث مقاييس المطعم
        await self._update_restaurant_metrics(
            restaurant_id=restaurant_id,
            action="category_deleted",
        )

        # تقليل عداد استخدام الميزة
        await decrease_usage(
            restaurant_id=restaurant_id,
            feature_id=CATEGORY_FEATURE_ID,
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
        category_order: List[int],
    ) -> None:
        """
        إعادة ترتيب التصنيفات.
        
        Args:
            restaurant_id: معرف المطعم
            category_order: قائمة معرفات التصنيفات بالترتيب الجديد
            
        Raises:
            NotFoundError: إذا كان أحد التصنيفات غير موجود
            ValidationError: إذا كانت القائمة فارغة أو تحتوي على معرفات مكررة
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
                message="قائمة ترتيب التصنيفات لا يمكن أن تكون فارغة",
            )

        # التحقق من عدم وجود معرفات مكررة
        if len(category_order) != len(set(category_order)):
            raise ValidationError(
                message="قائمة ترتيب التصنيفات تحتوي على معرفات مكررة",
            )

        # تحديث ترتيب كل تصنيف
        for index, category_id in enumerate(category_order):
            category = await self.repo.get_by_id(id=category_id)

            if not category:
                raise NotFoundError(
                    message=f"التصنيف بـ ID '{category_id}' غير موجود",
                )

            if category.restaurant_id != restaurant_id:
                raise ValidationError(
                    message=f"التصنيف '{category_id}' لا ينتمي لهذا المطعم",
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
        
        Args:
            restaurant_id: معرف المطعم
            action: نوع الإجراء (category_created, category_deleted)
        """
        try:
            # الحصول على المقاييس الحالية
            metrics = await self.metrics_repo.get_by_id(id=restaurant_id)

            if metrics:
                # تحديث المقاييس الموجودة
                if action == "category_created":
                    await self.metrics_repo.update(
                        id=restaurant_id,
                        data={"categories_count": metrics.categories_count + 1},
                    )
                elif action == "category_deleted":
                    await self.metrics_repo.update(
                        id=restaurant_id,
                        data={"categories_count": max(0, metrics.categories_count - 1)},
                    )
            else:
                # إنشاء مقاييس جديدة
                await self.metrics_repo.create(
                    data={
                        "restaurant_id": restaurant_id,
                        "products_count": 0,
                        "categories_count": 1 if action == "category_created" else 0,
                        "monthly_orders": 0,
                        "average_order_value": 0,
                    },
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
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE RESTAURANT CATEGORY (COMPATIBILITY)
# ==============================================

async def create_restaurant_category(
    *,
    restaurant_id: int,
    name: str,
    sort_order: int = 0,
    session: AsyncSession,
) -> int:
    """
    إنشاء تصنيف جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        name: اسم التصنيف
        sort_order: ترتيب العرض
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف التصنيف
        
    Raises:
        ConflictError: إذا كان الاسم موجوداً مسبقاً
    """
    service = CategoryService(session=session)

    category_data = CategoryCreate(
        name=name,
        sort_order=sort_order,
    )

    category = await service.create_category(
        restaurant_id=restaurant_id,
        category_data=category_data,
        skip_feature_check=True,
    )

    return category.id


# ==============================================
# GET CATEGORY (COMPATIBILITY)
# ==============================================

async def get_category(
    *,
    category_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على تصنيف بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        category_id: معرف التصنيف
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات التصنيف أو None
    """
    service = CategoryService(session=session)

    try:
        category = await service.get_by_id(category_id=category_id)
        return category.model_dump()
    except NotFoundError:
        return None


# ==============================================
# GET CATEGORIES (COMPATIBILITY)
# ==============================================

async def get_categories(
    *,
    restaurant_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على تصنيفات مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        List[Dict[str, Any]]: قائمة التصنيفات
    """
    service = CategoryService(session=session)

    result = await service.get_by_restaurant(
        restaurant_id=restaurant_id,
        skip=skip,
        limit=limit,
    )

    return [item.model_dump() for item in result.items]


# ==============================================
# REMOVE CATEGORY (COMPATIBILITY)
# ==============================================

async def remove_category(
    *,
    category_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف تصنيف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        category_id: معرف التصنيف
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على التصنيف
        ValidationError: إذا كان التصنيف يحتوي على منتجات
    """
    service = CategoryService(session=session)

    await service.delete_category(category_id=category_id)

    logger.info(
        "category_deleted",
        extra={"category_id": category_id},
    )


# ==============================================
# GET CATEGORIES COUNT (COMPATIBILITY)
# ==============================================

async def get_categories_count(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> int:
    """
    حساب عدد تصنيفات مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: عدد التصنيفات
    """
    service = CategoryService(session=session)

    return await service.count_by_restaurant(
        restaurant_id=restaurant_id,
    )


# ==============================================
# REORDER CATEGORIES (COMPATIBILITY)
# ==============================================

async def reorder_categories(
    *,
    restaurant_id: int,
    category_order: List[int],
    session: AsyncSession,
) -> None:
    """
    إعادة ترتيب التصنيفات (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        category_order: قائمة معرفات التصنيفات بالترتيب الجديد
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا كان أحد التصنيفات غير موجود
        ValidationError: إذا كانت القائمة فارغة أو تحتوي على معرفات مكررة
    """
    service = CategoryService(session=session)

    await service.reorder_categories(
        restaurant_id=restaurant_id,
        category_order=category_order,
    )

    logger.info(
        "categories_reordered",
        extra={
            "restaurant_id": restaurant_id,
            "category_count": len(category_order),
        },
    )