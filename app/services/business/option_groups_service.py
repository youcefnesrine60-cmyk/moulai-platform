# ==============================================
# 🎛 OPTION GROUPS SERVICE
# منطق الأعمال لمجموعات الخيارات
#
# إنشاء مجموعة خيارات
# قراءة مجموعة خيارات
# قراءة مجموعات خيارات المنتج
# قراءة مجموعات الخيارات الإجبارية
# تحديث مجموعة خيارات
# حذف مجموعة خيارات
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
from app.models.option_group import OptionGroup
from app.repositories.option_groups_repo import OptionGroupsRepository
from app.repositories.products_repo import ProductRepository

# ✅ استيراد المخططات
from app.schemas.option_group import (
    OptionGroupCreate,
    OptionGroupResponse,
    OptionGroupUpdate,
    OptionGroupWithOptionsResponse,
    OptionGroupSummary,
)


# ==============================================
# 🧩 CONSTANTS
# ==============================================

MAX_OPTION_GROUPS_PER_PRODUCT = 10


# ==============================================
# 🧩 TYPES
# ==============================================

OptionGroupData = Dict[str, Any]
OptionGroupUpdateData = Dict[str, Any]
OptionGroupList = List[OptionGroup]


# ==============================================
# 🎛 OPTION GROUPS SERVICE
# ==============================================


class OptionGroupsService:
    """
    خدمة مجموعات الخيارات - تدير منطق الأعمال لمجموعات الخيارات.
    
    مسؤولة عن:
        - إنشاء مجموعات الخيارات
        - قراءة مجموعات الخيارات
        - تحديث مجموعات الخيارات
        - حذف مجموعات الخيارات
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع مجموعات الخيارات
        product_repo: مستودع المنتجات
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة مجموعات الخيارات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = OptionGroupsRepository(session)
        self.product_repo = ProductRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        group_id: int,
    ) -> OptionGroupResponse:
        """
        الحصول على مجموعة خيارات بالمعرف.
        
        Args:
            group_id: معرف مجموعة الخيارات
            
        Returns:
            OptionGroupResponse: بيانات مجموعة الخيارات
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "option_groups_service_get_by_id",
            extra={"group_id": group_id},
        )

        group = await self.repo.get_by_id(
            id=group_id,
        )

        if not group:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        return OptionGroupResponse.model_validate(group)

    # ==============================================
    # GET BY PRODUCT
    # ==============================================

    async def get_by_product(
        self,
        *,
        product_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OptionGroupResponse]:
        """
        الحصول على مجموعات خيارات منتج معين.
        
        Args:
            product_id: معرف المنتج
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[OptionGroupResponse]: قائمة مجموعات الخيارات
        """
        logger.info(
            "option_groups_service_get_by_product",
            extra={
                "product_id": product_id,
                "skip": skip,
                "limit": limit,
            },
        )

        groups = await self.repo.get_by_product_id(
            product_id=product_id,
            skip=skip,
            limit=limit,
        )

        return [OptionGroupResponse.model_validate(group) for group in groups]

    # ==============================================
    # GET WITH OPTIONS
    # ==============================================

    async def get_with_options(
        self,
        *,
        group_id: int,
    ) -> OptionGroupWithOptionsResponse:
        """
        الحصول على مجموعة خيارات مع خياراتها.
        
        Args:
            group_id: معرف مجموعة الخيارات
            
        Returns:
            OptionGroupWithOptionsResponse: مجموعة الخيارات مع الخيارات
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "option_groups_service_get_with_options",
            extra={"group_id": group_id},
        )

        group = await self.repo.get_with_options(
            group_id=group_id,
        )

        if not group:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        return OptionGroupWithOptionsResponse.model_validate(group)

    # ==============================================
    # GET REQUIRED BY PRODUCT
    # ==============================================

    async def get_required_by_product(
        self,
        *,
        product_id: int,
    ) -> List[OptionGroupResponse]:
        """
        الحصول على مجموعات الخيارات الإجبارية لمنتج معين.
        
        Args:
            product_id: معرف المنتج
            
        Returns:
            List[OptionGroupResponse]: قائمة مجموعات الخيارات الإجبارية
        """
        logger.info(
            "option_groups_service_get_required_by_product",
            extra={"product_id": product_id},
        )

        groups = await self.repo.get_required_by_product(
            product_id=product_id,
        )

        return [OptionGroupResponse.model_validate(group) for group in groups]

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        product_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OptionGroupResponse]:
        """
        البحث عن مجموعات خيارات.
        
        Args:
            query: نص البحث
            product_id: معرف المنتج (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[OptionGroupResponse]: قائمة مجموعات الخيارات
        """
        # تنظيف النص
        clean_query = sanitize_input(query)

        logger.info(
            "option_groups_service_search",
            extra={
                "query": clean_query,
                "product_id": product_id,
                "skip": skip,
                "limit": limit,
            },
        )

        groups = await self.repo.search(
            query=clean_query,
            product_id=product_id,
            skip=skip,
            limit=limit,
        )

        return [OptionGroupResponse.model_validate(group) for group in groups]

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY PRODUCT
    # ==============================================

    async def count_by_product(
        self,
        *,
        product_id: int,
    ) -> int:
        """
        حساب عدد مجموعات الخيارات لمنتج معين.
        
        Args:
            product_id: معرف المنتج
            
        Returns:
            int: عدد مجموعات الخيارات
        """
        return await self.repo.count_by_product(
            product_id=product_id,
        )

    # ==============================================
    # COUNT REQUIRED BY PRODUCT
    # ==============================================

    async def count_required_by_product(
        self,
        *,
        product_id: int,
    ) -> int:
        """
        حساب عدد مجموعات الخيارات الإجبارية لمنتج معين.
        
        Args:
            product_id: معرف المنتج
            
        Returns:
            int: عدد مجموعات الخيارات الإجبارية
        """
        return await self.repo.count_required_by_product(
            product_id=product_id,
        )

    # ==============================================
    # GET OPTION GROUP SUMMARY
    # ==============================================

    async def get_option_group_summary(
        self,
        *,
        product_id: int,
    ) -> OptionGroupSummary:
        """
        الحصول على ملخص مجموعات الخيارات لمنتج معين.
        
        Args:
            product_id: معرف المنتج
            
        Returns:
            OptionGroupSummary: ملخص مجموعات الخيارات
        """
        logger.info(
            "option_groups_service_get_option_group_summary",
            extra={"product_id": product_id},
        )

        total = await self.count_by_product(
            product_id=product_id,
        )

        required = await self.count_required_by_product(
            product_id=product_id,
        )

        return OptionGroupSummary(
            total_groups=total,
            required_groups=required,
            optional_groups=total - required,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE GROUP
    # ==============================================

    async def create_group(
        self,
        *,
        group_data: OptionGroupCreate,
    ) -> OptionGroupResponse:
        """
        إنشاء مجموعة خيارات جديدة.
        
        Args:
            group_data: بيانات مجموعة الخيارات
            
        Returns:
            OptionGroupResponse: بيانات مجموعة الخيارات المنشأة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المنتج
            ConflictError: إذا كان الاسم موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صحيحة
        """
        # تنظيف الاسم
        name = sanitize_input(group_data.name)

        logger.info(
            "option_groups_service_create",
            extra={
                "product_id": group_data.product_id,
                "option_group_name": name,
            },
        )

        # التحقق من وجود المنتج
        product = await self.product_repo.get_by_id(
            restaurant_id=group_data.product_id,
        )

        if not product:
            raise NotFoundError(
                message=f"المنتج بـ ID '{group_data.product_id}' غير موجود",
            )

        # التحقق من الحد الأقصى لمجموعات الخيارات
        current_count = await self.count_by_product(
            product_id=group_data.product_id,
        )

        if current_count >= MAX_OPTION_GROUPS_PER_PRODUCT:
            raise ValidationError(
                message=f"تجاوزت الحد الأقصى لمجموعات الخيارات ({MAX_OPTION_GROUPS_PER_PRODUCT})",
                details={
                    "product_id": group_data.product_id,
                    "current_count": current_count,
                    "max_allowed": MAX_OPTION_GROUPS_PER_PRODUCT,
                },
            )

        # التحقق من عدم وجود مجموعة بنفس الاسم
        existing = await self.repo.get_by_name(
            product_id=group_data.product_id,
            name=name,
        )

        if existing:
            raise ConflictError(
                message=f"مجموعة الخيارات '{name}' موجودة بالفعل لهذا المنتج",
            )

        # إنشاء مجموعة الخيارات
        data: OptionGroupData = {
            "product_id": group_data.product_id,
            "name": name,
            "required": group_data.required or False,
            "multiple_choice": group_data.multiple_choice or False,
            "sort_order": group_data.sort_order or 0,
        }

        group = await self.repo.create(data=data)

        logger.info(
            "option_group_created_successfully",
            extra={
                "group_id": group.id,
                "product_id": group_data.product_id,
            },
        )

        return OptionGroupResponse.model_validate(group)

    # ==============================================
    # UPDATE GROUP
    # ==============================================

    async def update_group(
        self,
        *,
        group_id: int,
        update_data: OptionGroupUpdate,
    ) -> OptionGroupResponse:
        """
        تحديث مجموعة خيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            update_data: بيانات التحديث
            
        Returns:
            OptionGroupResponse: بيانات مجموعة الخيارات المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
            ConflictError: إذا كان الاسم موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صحيحة
        """
        logger.info(
            "option_groups_service_update",
            extra={
                "group_id": group_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود المجموعة
        existing = await self.repo.get_by_id(id=group_id)

        if not existing:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف الاسم إذا تم تغييره
        if "name" in updates:
            updates["name"] = sanitize_input(updates["name"])

            # التحقق من عدم وجود اسم مكرر
            duplicate = await self.repo.get_by_name(
                product_id=existing.product_id,
                name=updates["name"],
            )

            if duplicate and duplicate.id != group_id:
                raise ConflictError(
                    message=f"مجموعة الخيارات '{updates['name']}' موجودة بالفعل",
                )

        # تحديث المجموعة
        updated = await self.repo.update(
            id=group_id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        logger.info(
            "option_group_updated_successfully",
            extra={
                "group_id": group_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return OptionGroupResponse.model_validate(updated)

    # ==============================================
    # UPDATE SORT ORDER
    # ==============================================

    async def update_sort_order(
        self,
        *,
        group_id: int,
        sort_order: int,
    ) -> OptionGroupResponse:
        """
        تحديث ترتيب مجموعة الخيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            sort_order: الترتيب الجديد
            
        Returns:
            OptionGroupResponse: بيانات مجموعة الخيارات المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "option_groups_service_update_sort_order",
            extra={
                "group_id": group_id,
                "sort_order": sort_order,
            },
        )

        group = await self.repo.update_sort_order(
            group_id=group_id,
            sort_order=sort_order,
        )

        if not group:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        logger.info(
            "option_group_sort_order_updated_successfully",
            extra={
                "group_id": group_id,
                "sort_order": sort_order,
            },
        )

        return OptionGroupResponse.model_validate(group)

    # ==============================================
    # UPDATE REQUIRED
    # ==============================================

    async def update_required(
        self,
        *,
        group_id: int,
        required: bool,
    ) -> OptionGroupResponse:
        """
        تحديث حالة الإجبار لمجموعة الخيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            required: حالة الإجبار الجديدة
            
        Returns:
            OptionGroupResponse: بيانات مجموعة الخيارات المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "option_groups_service_update_required",
            extra={
                "group_id": group_id,
                "required": required,
            },
        )

        group = await self.repo.update_required(
            group_id=group_id,
            required=required,
        )

        if not group:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        logger.info(
            "option_group_required_updated_successfully",
            extra={
                "group_id": group_id,
                "required": required,
            },
        )

        return OptionGroupResponse.model_validate(group)

    # ==============================================
    # UPDATE MULTIPLE CHOICE
    # ==============================================

    async def update_multiple_choice(
        self,
        *,
        group_id: int,
        multiple_choice: bool,
    ) -> OptionGroupResponse:
        """
        تحديث حالة الاختيار المتعدد لمجموعة الخيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            multiple_choice: حالة الاختيار المتعدد الجديدة
            
        Returns:
            OptionGroupResponse: بيانات مجموعة الخيارات المحدثة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
        """
        logger.info(
            "option_groups_service_update_multiple_choice",
            extra={
                "group_id": group_id,
                "multiple_choice": multiple_choice,
            },
        )

        group = await self.repo.update_multiple_choice(
            group_id=group_id,
            multiple_choice=multiple_choice,
        )

        if not group:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        logger.info(
            "option_group_multiple_choice_updated_successfully",
            extra={
                "group_id": group_id,
                "multiple_choice": multiple_choice,
            },
        )

        return OptionGroupResponse.model_validate(group)

    # ==============================================
    # DELETE GROUP
    # ==============================================

    async def delete_group(
        self,
        *,
        group_id: int,
    ) -> None:
        """
        حذف مجموعة خيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المجموعة
            ValidationError: إذا كانت المجموعة تحتوي على خيارات
        """
        logger.info(
            "option_groups_service_delete",
            extra={"group_id": group_id},
        )

        # التحقق من وجود المجموعة
        existing = await self.repo.get_by_id(id=group_id)

        if not existing:
            raise NotFoundError(
                message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
            )

        # التحقق من عدم وجود خيارات في هذه المجموعة
        options_count = await self.repo.count_options_in_group(
            group_id=group_id,
        )

        if options_count > 0:
            raise ValidationError(
                message="لا يمكن حذف مجموعة الخيارات لأنها تحتوي على خيارات",
                details={
                    "group_id": group_id,
                    "options_count": options_count,
                },
            )

        # حذف المجموعة
        await self.repo.delete(id=group_id)

        logger.info(
            "option_group_deleted_successfully",
            extra={"group_id": group_id},
        )

    # ==============================================
    # DELETE BY PRODUCT
    # ==============================================

    async def delete_by_product(
        self,
        *,
        product_id: int,
    ) -> int:
        """
        حذف جميع مجموعات الخيارات لمنتج معين.
        
        Args:
            product_id: معرف المنتج
            
        Returns:
            int: عدد المجموعات المحذوفة
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المنتج
        """
        logger.info(
            "option_groups_service_delete_by_product",
            extra={"product_id": product_id},
        )

        # التحقق من وجود المنتج
        product = await self.product_repo.get_by_id(
            restaurant_id=product_id,
        )

        if not product:
            raise NotFoundError(
                message=f"المنتج بـ ID '{product_id}' غير موجود",
            )

        # حذف المجموعات
        count = await self.repo.delete_by_product(
            product_id=product_id,
        )

        logger.info(
            "option_groups_deleted_by_product_successfully",
            extra={
                "product_id": product_id,
                "count": count,
            },
        )

        return count

    # ==============================================
    # REORDER GROUPS
    # ==============================================

    async def reorder_groups(
        self,
        *,
        product_id: int,
        group_order: List[int],
    ) -> None:
        """
        إعادة ترتيب مجموعات الخيارات.
        
        Args:
            product_id: معرف المنتج
            group_order: قائمة معرفات المجموعات بالترتيب الجديد
            
        Raises:
            NotFoundError: إذا كان أحد المجموعات غير موجود
            ValidationError: إذا كانت القائمة فارغة أو تحتوي على معرفات مكررة
        """
        logger.info(
            "option_groups_service_reorder",
            extra={
                "product_id": product_id,
                "group_count": len(group_order),
            },
        )

        if not group_order:
            raise ValidationError(
                message="قائمة ترتيب مجموعات الخيارات لا يمكن أن تكون فارغة",
            )

        # التحقق من عدم وجود معرفات مكررة
        if len(group_order) != len(set(group_order)):
            raise ValidationError(
                message="قائمة ترتيب مجموعات الخيارات تحتوي على معرفات مكررة",
            )

        # تحديث ترتيب كل مجموعة
        for index, group_id in enumerate(group_order):
            group = await self.repo.get_by_id(id=group_id)

            if not group:
                raise NotFoundError(
                    message=f"مجموعة الخيارات بـ ID '{group_id}' غير موجودة",
                )

            if group.product_id != product_id:
                raise ValidationError(
                    message=f"مجموعة الخيارات '{group_id}' لا تنتمي لهذا المنتج",
                )

            await self.repo.update_sort_order(
                group_id=group_id,
                sort_order=index,
            )

        logger.info(
            "option_groups_reordered_successfully",
            extra={
                "product_id": product_id,
                "group_count": len(group_order),
            },
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE OPTION GROUP (COMPATIBILITY)
# ==============================================

async def create_option_group(
    *,
    product_id: int,
    name: str,
    required: bool = False,
    multiple_choice: bool = False,
    sort_order: int = 0,
    session: AsyncSession,
) -> int:
    """
    إنشاء مجموعة خيارات جديدة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        product_id: معرف المنتج
        name: اسم مجموعة الخيارات
        required: هل المجموعة إجبارية
        multiple_choice: هل يسمح باختيار متعدد
        sort_order: ترتيب العرض
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف مجموعة الخيارات
        
    Raises:
        NotFoundError: إذا لم يتم العثور على المنتج
        ConflictError: إذا كان الاسم موجوداً مسبقاً
    """
    service = OptionGroupsService(session=session)

    group_data = OptionGroupCreate(
        product_id=product_id,
        name=name,
        required=required,
        multiple_choice=multiple_choice,
        sort_order=sort_order,
    )

    group = await service.create_group(
        group_data=group_data,
    )

    return group.id


# ==============================================
# GET OPTION GROUP (COMPATIBILITY)
# ==============================================

async def get_option_group(
    *,
    group_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مجموعة خيارات بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        group_id: معرف مجموعة الخيارات
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات المجموعة أو None
    """
    service = OptionGroupsService(session=session)

    try:
        group = await service.get_by_id(group_id=group_id)
        return group.model_dump()
    except NotFoundError:
        return None


# ==============================================
# GET OPTION GROUPS (COMPATIBILITY)
# ==============================================

async def get_option_groups(
    *,
    product_id: int,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على مجموعات خيارات منتج معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        product_id: معرف المنتج
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        List[Dict[str, Any]]: قائمة مجموعات الخيارات
    """
    service = OptionGroupsService(session=session)

    groups = await service.get_by_product(
        product_id=product_id,
        skip=skip,
        limit=limit,
    )

    return [group.model_dump() for group in groups]


# ==============================================
# DELETE OPTION GROUP (COMPATIBILITY)
# ==============================================

async def delete_option_group(
    *,
    group_id: int,
    session: AsyncSession,
) -> None:
    """
    حذف مجموعة خيارات (دالة متوافقة مع الإصدار القديم).
    
    Args:
        group_id: معرف مجموعة الخيارات
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على المجموعة
        ValidationError: إذا كانت المجموعة تحتوي على خيارات
    """
    service = OptionGroupsService(session=session)

    await service.delete_group(group_id=group_id)

    logger.info(
        "option_group_deleted",
        extra={"group_id": group_id},
    )


# ==============================================
# GET OPTION GROUPS COUNT (COMPATIBILITY)
# ==============================================

async def get_option_groups_count(
    *,
    product_id: int,
    session: AsyncSession,
) -> int:
    """
    حساب عدد مجموعات الخيارات لمنتج معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        product_id: معرف المنتج
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: عدد مجموعات الخيارات
    """
    service = OptionGroupsService(session=session)

    return await service.count_by_product(
        product_id=product_id,
    )
