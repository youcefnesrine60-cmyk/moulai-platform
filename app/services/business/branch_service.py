# ==============================================
# 🏢 BRANCH SERVICE
# Business Logic Layer
# منطق الأعمال للفروع
#
# إنشاء فرع
# تحديث فرع
# إلغاء تفعيل فرع
# قائمة الفروع
# حساب عدد الفروع
# حساب تكلفة الفروع
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
    BranchLimitExceededError,
)

# ✅ استيراد دوال الأمان (للتحقق من الصلاحيات)
from app.core.security import (
    sanitize_input,
)

from app.core.logger import logger
from app.models.branch import Branch
from app.repositories.branches_repo import BranchesRepository
from app.repositories.branch_pricing_repo import BranchPricingRepository
from app.services.business.feature_usage_counter_engine import (
    decrease_usage,
    increase_usage,
)

# ✅ استيراد المخططات
from app.schemas.branch import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
    BranchStatusUpdate,
    BranchListResponse,
    BranchSummary,
)


# ==============================================
# 🧩 CONSTANTS
# ==============================================

BRANCH_FEATURE_ID = 3
MAX_BRANCHES_PER_RESTAURANT = 10


# ==============================================
# 🧩 TYPES
# ==============================================

BranchData = Dict[str, Any]
BranchList = List[Branch]


# ==============================================
# 🏢 BRANCH SERVICE
# ==============================================


class BranchService:
    """
    خدمة الفروع - تدير منطق الأعمال للفروع.
    
    مسؤولة عن:
        - إنشاء وإدارة الفروع
        - تحديث حالة النشاط
        - حساب تكلفة الفروع
        - إدارة عداد استخدام الميزات
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع الفروع
        pricing_repo: مستودع تسعير الفروع
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة الفروع.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = BranchesRepository(session)
        self.pricing_repo = BranchPricingRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        branch_id: int,
    ) -> BranchResponse:
        """
        الحصول على فرع بالمعرف.
        
        Args:
            branch_id: معرف الفرع
            
        Returns:
            BranchResponse: بيانات الفرع
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_get_by_id",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id(
            id=branch_id,
        )

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        return BranchResponse.model_validate(branch)

    # ==============================================
    # GET BY RESTAURANT
    # ==============================================

    async def get_by_restaurant(
        self,
        *,
        restaurant_id: int,
        skip: int = 0,
        limit: int = 100,
        only_active: bool = True,
    ) -> BranchListResponse:
        """
        الحصول على فروع مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_active: جلب الفروع النشطة فقط
            
        Returns:
            BranchListResponse: قائمة الفروع مع الإحصائيات
        """
        logger.info(
            "branch_service_get_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
                "only_active": only_active,
            },
        )

        branches = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
            only_active=only_active,
        )

        total = await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=only_active,
        )

        return BranchListResponse(
            items=[BranchResponse.model_validate(branch) for branch in branches],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==============================================
    # COUNT BY RESTAURANT
    # ==============================================

    async def count_by_restaurant(
        self,
        *,
        restaurant_id: int,
        only_active: bool = True,
    ) -> int:
        """
        حساب عدد فروع مطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            only_active: حساب الفروع النشطة فقط
            
        Returns:
            int: عدد الفروع
        """
        logger.info(
            "branch_service_count_by_restaurant",
            extra={
                "restaurant_id": restaurant_id,
                "only_active": only_active,
            },
        )

        return await self.repo.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=only_active,
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
    ) -> BranchListResponse:
        """
        البحث عن فروع.
        
        Args:
            query: نص البحث
            restaurant_id: معرف المطعم (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            BranchListResponse: قائمة الفروع مع الإحصائيات
        """
        # تنظيف النص
        clean_query = sanitize_input(query)

        logger.info(
            "branch_service_search",
            extra={
                "query": clean_query,
                "restaurant_id": restaurant_id,
                "skip": skip,
                "limit": limit,
            },
        )

        branches = await self.repo.search(
            query=clean_query,
            restaurant_id=restaurant_id,
            skip=skip,
            limit=limit,
        )

        total = len(branches)

        return BranchListResponse(
            items=[BranchResponse.model_validate(branch) for branch in branches],
            total=total,
            skip=skip,
            limit=limit,
        )

    # ==========================================
    # 💰 PRICING
    # ==========================================

    # ==============================================
    # GET BRANCH COST
    # ==============================================

    async def get_branch_cost(
        self,
        *,
        restaurant_id: int,
    ) -> float:
        """
        حساب تكلفة الفروع لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            float: التكلفة الإجمالية للفروع
        """
        branches_count = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
        )

        cost = await self.pricing_repo.calculate_cost(
            branches_count=branches_count,
        )

        logger.info(
            "branch_service_get_branch_cost",
            extra={
                "restaurant_id": restaurant_id,
                "branches_count": branches_count,
                "cost": cost,
            },
        )

        return cost

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET BRANCH SUMMARY
    # ==============================================

    async def get_branch_summary(
        self,
        *,
        restaurant_id: int,
    ) -> BranchSummary:
        """
        الحصول على ملخص الفروع لمطعم معين.
        
        Args:
            restaurant_id: معرف المطعم
            
        Returns:
            BranchSummary: ملخص الفروع
        """
        logger.info(
            "branch_service_get_branch_summary",
            extra={"restaurant_id": restaurant_id},
        )

        total = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=False,
        )

        active = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=True,
        )

        inactive = total - active

        total_cost = await self.get_branch_cost(
            restaurant_id=restaurant_id,
        )

        # توزيع الفروع حسب الولاية
        branches = await self.repo.get_by_restaurant_id(
            restaurant_id=restaurant_id,
            only_active=False,
            limit=1000,
        )

        branches_per_wilaya: Dict[str, int] = {}

        for branch in branches:
            wilaya = branch.wilaya or "غير محدد"
            branches_per_wilaya[wilaya] = branches_per_wilaya.get(wilaya, 0) + 1

        return BranchSummary(
            total_branches=total,
            active_branches=active,
            inactive_branches=inactive,
            total_cost=total_cost,
            branches_per_wilaya=branches_per_wilaya,
        )

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE BRANCH
    # ==============================================

    async def create_branch(
        self,
        *,
        restaurant_id: int,
        branch_data: BranchCreate,
        skip_feature_check: bool = False,
    ) -> BranchResponse:
        """
        إنشاء فرع جديد.
        
        Args:
            restaurant_id: معرف المطعم
            branch_data: بيانات الفرع
            skip_feature_check: تخطي التحقق من الميزة (للاستخدام الداخلي)
            
        Returns:
            BranchResponse: بيانات الفرع المنشأ
            
        Raises:
            BranchLimitExceededError: إذا تجاوز المطعم الحد الأقصى للفروع
            ValidationError: إذا كانت البيانات غير صحيحة
        """
        # تنظيف البيانات
        name = sanitize_input(branch_data.name)

        logger.info(
            "branch_service_create",
            extra={
                "restaurant_id": restaurant_id,
                "branch_name": name,
            },
        )

        # التحقق من الحد الأقصى للفروع
        current_count = await self.count_by_restaurant(
            restaurant_id=restaurant_id,
            only_active=True,
        )

        if current_count >= MAX_BRANCHES_PER_RESTAURANT:
            raise BranchLimitExceededError(
                restaurant_id=restaurant_id,
                max_branches=MAX_BRANCHES_PER_RESTAURANT,
                message=f"تجاوزت الحد الأقصى للفروع ({MAX_BRANCHES_PER_RESTAURANT})",
            )

        # التحقق من الميزة (Feature Guard)
        # TODO: إعادة تفعيل require_feature بعد اكتمال النظام
        # if not skip_feature_check:
        #     await require_feature(
        #         restaurant_id=restaurant_id,
        #         feature_id=BRANCH_FEATURE_ID,
        #     )

        # التحقق من عدم وجود فرع بنفس الاسم للمطعم
        existing = await self.repo.get_by_name(
            restaurant_id=restaurant_id,
            name=name,
        )

        if existing:
            raise ConflictError(
                message=f"يوجد فرع باسم '{name}' بالفعل لهذا المطعم",
            )

        # إنشاء الفرع
        data: BranchData = {
            "restaurant_id": restaurant_id,
            "name": name,
            "phone": branch_data.phone,
            "wilaya": branch_data.wilaya,
            "lat": branch_data.lat,
            "lng": branch_data.lng,
            "is_active": True,
        }

        branch = await self.repo.create(data=data)

        # زيادة عداد استخدام الميزة
        await increase_usage(
            restaurant_id=restaurant_id,
            feature_id=BRANCH_FEATURE_ID,
        )

        logger.info(
            "branch_created_successfully",
            extra={
                "branch_id": branch.id,
                "restaurant_id": restaurant_id,
            },
        )

        return BranchResponse.model_validate(branch)

    # ==============================================
    # UPDATE BRANCH
    # ==============================================

    async def update_branch(
        self,
        *,
        branch_id: int,
        update_data: BranchUpdate,
    ) -> BranchResponse:
        """
        تحديث فرع.
        
        Args:
            branch_id: معرف الفرع
            update_data: بيانات التحديث
            
        Returns:
            BranchResponse: بيانات الفرع المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
            ConflictError: إذا كان الاسم موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صحيحة
        """
        logger.info(
            "branch_service_update",
            extra={
                "branch_id": branch_id,
                "update_data": update_data.model_dump(exclude_unset=True),
            },
        )

        # التحقق من وجود الفرع
        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف الاسم إذا تم تغييره
        if "name" in updates:
            updates["name"] = sanitize_input(updates["name"])

            # التحقق من عدم وجود اسم مكرر
            existing = await self.repo.get_by_name(
                restaurant_id=branch.restaurant_id,
                name=updates["name"],
            )

            if existing and existing.id != branch_id:
                raise ConflictError(
                    message=f"يوجد فرع باسم '{updates['name']}' بالفعل لهذا المطعم",
                )

        # تحديث الفرع
        updated = await self.repo.update(
            id=branch_id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        logger.info(
            "branch_updated_successfully",
            extra={
                "branch_id": branch_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return BranchResponse.model_validate(updated)

    # ==============================================
    # UPDATE BRANCH STATUS
    # ==============================================

    async def update_branch_status(
        self,
        *,
        branch_id: int,
        status_data: BranchStatusUpdate,
    ) -> BranchResponse:
        """
        تحديث حالة الفرع (نشط/غير نشط).
        
        Args:
            branch_id: معرف الفرع
            status_data: بيانات الحالة
            
        Returns:
            BranchResponse: بيانات الفرع المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_update_status",
            extra={
                "branch_id": branch_id,
                "is_active": status_data.is_active,
            },
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        if status_data.is_active:
            # تفعيل الفرع
            updated = await self.activate_branch(branch_id=branch_id)
        else:
            # إلغاء تفعيل الفرع
            updated = await self.deactivate_branch(branch_id=branch_id)

        return BranchResponse.model_validate(updated)

    # ==============================================
    # DEACTIVATE BRANCH
    # ==============================================

    async def deactivate_branch(
        self,
        *,
        branch_id: int,
    ) -> Branch:
        """
        إلغاء تفعيل فرع.
        
        Args:
            branch_id: معرف الفرع
            
        Returns:
            Branch: كائن الفرع المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_deactivate",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        restaurant_id = branch.restaurant_id

        # إلغاء تفعيل الفرع
        updated = await self.repo.deactivate(branch_id=branch_id)

        if not updated:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        # تقليل عداد استخدام الميزة
        await decrease_usage(
            restaurant_id=restaurant_id,
            feature_id=BRANCH_FEATURE_ID,
        )

        logger.info(
            "branch_deactivated_successfully",
            extra={
                "branch_id": branch_id,
                "restaurant_id": restaurant_id,
            },
        )

        return updated

    # ==============================================
    # ACTIVATE BRANCH
    # ==============================================

    async def activate_branch(
        self,
        *,
        branch_id: int,
    ) -> Branch:
        """
        تفعيل فرع.
        
        Args:
            branch_id: معرف الفرع
            
        Returns:
            Branch: كائن الفرع المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_activate",
            extra={"branch_id": branch_id},
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        restaurant_id = branch.restaurant_id

        # تفعيل الفرع
        updated = await self.repo.activate(branch_id=branch_id)

        if not updated:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        # زيادة عداد استخدام الميزة
        await increase_usage(
            restaurant_id=restaurant_id,
            feature_id=BRANCH_FEATURE_ID,
        )

        logger.info(
            "branch_activated_successfully",
            extra={
                "branch_id": branch_id,
                "restaurant_id": restaurant_id,
            },
        )

        return updated

    # ==============================================
    # DELETE BRANCH
    # ==============================================

    async def delete_branch(
        self,
        *,
        branch_id: int,
        permanent: bool = False,
    ) -> None:
        """
        حذف فرع.
        
        Args:
            branch_id: معرف الفرع
            permanent: حذف فعلي (بدلاً من الحذف المنطقي)
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الفرع
        """
        logger.info(
            "branch_service_delete",
            extra={
                "branch_id": branch_id,
                "permanent": permanent,
            },
        )

        branch = await self.repo.get_by_id(id=branch_id)

        if not branch:
            raise NotFoundError(
                message=f"الفرع بـ ID '{branch_id}' غير موجود",
            )

        restaurant_id = branch.restaurant_id

        if permanent:
            # حذف فعلي
            await self.repo.delete(id=branch_id)
        else:
            # حذف منطقي (تعيين is_active = False)
            await self.repo.deactivate(branch_id=branch_id)

        # تقليل عداد استخدام الميزة
        await decrease_usage(
            restaurant_id=restaurant_id,
            feature_id=BRANCH_FEATURE_ID,
        )

        logger.info(
            "branch_deleted_successfully",
            extra={
                "branch_id": branch_id,
                "restaurant_id": restaurant_id,
                "permanent": permanent,
            },
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# CREATE RESTAURANT BRANCH (COMPATIBILITY)
# ==============================================

async def create_restaurant_branch(
    *,
    restaurant_id: int,
    name: str,
    phone: Optional[str],
    wilaya: Optional[str],
    lat: Optional[float],
    lng: Optional[float],
    session: AsyncSession,
) -> int:
    """
    إنشاء فرع جديد (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        name: اسم الفرع
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف الفرع
    """
    service = BranchService(session=session)

    branch_data = BranchCreate(
        name=name,
        phone=phone,
        wilaya=wilaya,
        lat=lat,
        lng=lng,
    )

    branch = await service.create_branch(
        restaurant_id=restaurant_id,
        branch_data=branch_data,
        skip_feature_check=True,
    )

    return branch.id


# ==============================================
# UPDATE RESTAURANT BRANCH (COMPATIBILITY)
# ==============================================

async def update_restaurant_branch(
    *,
    branch_id: int,
    name: str,
    phone: Optional[str],
    wilaya: Optional[str],
    lat: Optional[float],
    lng: Optional[float],
    session: AsyncSession,
) -> None:
    """
    تحديث فرع (دالة متوافقة مع الإصدار القديم).
    
    Args:
        branch_id: معرف الفرع
        name: اسم الفرع
        phone: رقم الهاتف
        wilaya: الولاية
        lat: خط العرض
        lng: خط الطول
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الفرع
    """
    service = BranchService(session=session)

    update_data = BranchUpdate(
        name=name,
        phone=phone,
        wilaya=wilaya,
        lat=lat,
        lng=lng,
    )

    await service.update_branch(
        branch_id=branch_id,
        update_data=update_data,
    )

    logger.info(
        "restaurant_branch_updated",
        extra={"branch_id": branch_id},
    )


# ==============================================
# REMOVE RESTAURANT BRANCH (COMPATIBILITY)
# ==============================================

async def remove_restaurant_branch(
    *,
    branch_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء تفعيل فرع (دالة متوافقة مع الإصدار القديم).
    
    Args:
        branch_id: معرف الفرع
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الفرع
    """
    service = BranchService(session=session)

    await service.deactivate_branch(branch_id=branch_id)

    logger.info(
        "restaurant_branch_removed",
        extra={"branch_id": branch_id},
    )


# ==============================================
# LIST RESTAURANT BRANCHES (COMPATIBILITY)
# ==============================================

async def list_restaurant_branches(
    *,
    restaurant_id: int,
    session: AsyncSession,
    only_active: bool = True,
) -> List[Dict[str, Any]]:
    """
    الحصول على فروع مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        only_active: جلب الفروع النشطة فقط
        
    Returns:
        List[Dict[str, Any]]: قائمة الفروع
    """
    service = BranchService(session=session)

    result = await service.get_by_restaurant(
        restaurant_id=restaurant_id,
        only_active=only_active,
    )

    return [item.model_dump() for item in result.items]


# ==============================================
# GET BRANCHES COUNT (COMPATIBILITY)
# ==============================================

async def get_branches_count(
    *,
    restaurant_id: int,
    session: AsyncSession,
    only_active: bool = True,
) -> int:
    """
    حساب عدد فروع مطعم معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        only_active: حساب الفروع النشطة فقط
        
    Returns:
        int: عدد الفروع
    """
    service = BranchService(session=session)

    return await service.count_by_restaurant(
        restaurant_id=restaurant_id,
        only_active=only_active,
    )


# ==============================================
# GET BRANCH COST (COMPATIBILITY)
# ==============================================

async def get_branch_cost(
    *,
    restaurant_id: int,
    session: AsyncSession,
) -> float:
    """
    حساب تكلفة الفروع (دالة متوافقة مع الإصدار القديم).
    
    Args:
        restaurant_id: معرف المطعم
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        float: التكلفة الإجمالية للفروع
    """
    service = BranchService(session=session)

    return await service.get_branch_cost(
        restaurant_id=restaurant_id,
    )