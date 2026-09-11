# ==============================================
# 📝 REGISTRATION REQUEST SERVICE
# منطق الأعمال لطلبات التسجيل
# يدير عمليات إنشاء واستعراض وتحديث وحذف طلبات التسجيل
#
# Registration Request
#        ↓
# Admin Approval
#        ↓
# Create Owner
#        ↓
# Create Restaurant
#        ↓
# Create Restaurant Metrics
#        ↓
# Create Trial Subscription
#        ↓
# Create Subscription Features
#        ↓
# Owner Approved
#        ↓
# Registration Request Approved
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
from app.models.registration_request import RegistrationRequest
from app.repositories.registration_request_repo import (
    RegistrationRequestRepository,
)
from app.repositories.restaurant.restaurant_repo import RestaurantRepository
from app.services.business.owner_service import OwnerService
from app.services.business.subscription_service import (
    SubscriptionService,
)

# ✅ استيراد المخططات
from app.schemas.registration_request import (
    RegistrationRequestCreate,
    RegistrationRequestResponse,
    RegistrationRequestUpdate,
    RegistrationRequestStatusUpdate,
)


# ==============================================
# 🧩 CONSTANTS
# ==============================================

VALID_REQUEST_STATUSES = {"pending", "approved", "rejected"}
MAX_REQUESTS_PER_CHAT = 3


# ==============================================
# 🧩 TYPES
# ==============================================

RegistrationResult = Dict[str, int]
RegistrationData = Dict[str, Any]
RegistrationUpdateData = Dict[str, Any]
RegistrationList = List[RegistrationRequest]


# ==============================================
# 📝 REGISTRATION REQUEST SERVICE
# ==============================================


class RegistrationRequestService:
    """
    خدمة طلبات التسجيل - تدير منطق الأعمال لطلبات التسجيل.
    
    مسؤولة عن:
        - إنشاء وإدارة طلبات التسجيل
        - الموافقة على الطلبات وإنشاء المالك والمطعم والاشتراك
        - رفض الطلبات
        - البحث والتصفية
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع طلبات التسجيل
        owner_service: خدمة المالكين
        restaurant_repo: مستودع المطاعم
        subscription_service: خدمة الاشتراكات
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة طلبات التسجيل.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = RegistrationRequestRepository(session)
        self.owner_service = OwnerService(session)
        self.restaurant_repo = RestaurantRepository(session)
        self.subscription_service = SubscriptionService(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        request_id: int,
    ) -> RegistrationRequestResponse:
        """
        الحصول على طلب تسجيل بالمعرف.
        
        Args:
            request_id: معرف طلب التسجيل
            
        Returns:
            RegistrationRequestResponse: بيانات طلب التسجيل
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
        """
        logger.info(
            "registration_request_service_get_by_id",
            extra={"request_id": request_id},
        )

        request = await self.repo.get_by_id(
            request_id=request_id,
        )

        if not request:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        return RegistrationRequestResponse.model_validate(request)

    # ==============================================
    # GET BY CHAT ID
    # ==============================================

    async def get_by_chat_id(
        self,
        *,
        chat_id: int,
    ) -> Optional[RegistrationRequestResponse]:
        """
        الحصول على طلب تسجيل بواسطة chat_id.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            Optional[RegistrationRequestResponse]: بيانات طلب التسجيل أو None
        """
        logger.info(
            "registration_request_service_get_by_chat_id",
            extra={"chat_id": chat_id},
        )

        request = await self.repo.get_by_chat_id(
            chat_id=chat_id,
        )

        if not request:
            return None

        return RegistrationRequestResponse.model_validate(request)

    # ==============================================
    # GET ALL BY CHAT ID
    # ==============================================

    async def get_all_by_chat_id(
        self,
        *,
        chat_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RegistrationRequestResponse]:
        """
        الحصول على جميع طلبات التسجيل لمستخدم معين.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RegistrationRequestResponse]: قائمة طلبات التسجيل
        """
        logger.info(
            "registration_request_service_get_all_by_chat_id",
            extra={
                "chat_id": chat_id,
                "skip": skip,
                "limit": limit,
            },
        )

        requests = await self.repo.get_all_by_chat_id(
            chat_id=chat_id,
            skip=skip,
            limit=limit,
        )

        return [RegistrationRequestResponse.model_validate(req) for req in requests]

    # ==============================================
    # GET BY STATUS
    # ==============================================

    async def get_by_status(
        self,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RegistrationRequestResponse]:
        """
        الحصول على طلبات التسجيل حسب الحالة.
        
        Args:
            status: حالة الطلب (pending, approved, rejected)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RegistrationRequestResponse]: قائمة طلبات التسجيل
            
        Raises:
            ValidationError: إذا كانت الحالة غير صالحة
        """
        if status not in VALID_REQUEST_STATUSES:
            raise ValidationError(
                message=f"حالة الطلب '{status}' غير صالحة",
                details={
                    "status": status,
                    "valid_statuses": list(VALID_REQUEST_STATUSES),
                },
            )

        logger.info(
            "registration_request_service_get_by_status",
            extra={
                "status": status,
                "skip": skip,
                "limit": limit,
            },
        )

        requests = await self.repo.get_by_status(
            status=status,
            skip=skip,
            limit=limit,
        )

        return [RegistrationRequestResponse.model_validate(req) for req in requests]

    # ==============================================
    # GET PENDING
    # ==============================================

    async def get_pending(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RegistrationRequestResponse]:
        """
        الحصول على طلبات التسجيل المعلقة.
        
        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RegistrationRequestResponse]: قائمة طلبات التسجيل المعلقة
        """
        logger.info(
            "registration_request_service_get_pending",
            extra={
                "skip": skip,
                "limit": limit,
            },
        )

        requests = await self.repo.get_pending(
            skip=skip,
            limit=limit,
        )

        return [RegistrationRequestResponse.model_validate(req) for req in requests]

    # ==============================================
    # GET ALL
    # ==============================================

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RegistrationRequestResponse]:
        """
        الحصول على جميع طلبات التسجيل.
        
        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RegistrationRequestResponse]: قائمة طلبات التسجيل
        """
        logger.info(
            "registration_request_service_get_all",
            extra={
                "skip": skip,
                "limit": limit,
            },
        )

        requests = await self.repo.get_all(
            skip=skip,
            limit=limit,
        )

        return [RegistrationRequestResponse.model_validate(req) for req in requests]

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[RegistrationRequestResponse]:
        """
        البحث عن طلبات التسجيل.
        
        Args:
            query: نص البحث
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[RegistrationRequestResponse]: قائمة طلبات التسجيل
        """
        clean_query = sanitize_input(query)

        logger.info(
            "registration_request_service_search",
            extra={
                "query": clean_query,
                "skip": skip,
                "limit": limit,
            },
        )

        requests = await self.repo.search(
            query=clean_query,
            skip=skip,
            limit=limit,
        )

        return [RegistrationRequestResponse.model_validate(req) for req in requests]

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT BY STATUS
    # ==============================================

    async def count_by_status(
        self,
        *,
        status: str,
    ) -> int:
        """
        حساب عدد طلبات التسجيل حسب الحالة.
        
        Args:
            status: حالة الطلب
            
        Returns:
            int: عدد الطلبات
        """
        if status not in VALID_REQUEST_STATUSES:
            raise ValidationError(
                message=f"حالة الطلب '{status}' غير صالحة",
                details={
                    "status": status,
                    "valid_statuses": list(VALID_REQUEST_STATUSES),
                },
            )

        return await self.repo.count_by_status(status=status)

    # ==============================================
    # COUNT PENDING
    # ==============================================

    async def count_pending(
        self,
    ) -> int:
        """
        حساب عدد طلبات التسجيل المعلقة.
        
        Returns:
            int: عدد الطلبات المعلقة
        """
        return await self.repo.count_pending()

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE
    # ==============================================

    async def create(
        self,
        *,
        request_data: RegistrationRequestCreate,
    ) -> RegistrationRequestResponse:
        """
        إنشاء طلب تسجيل جديد.
        
        Args:
            request_data: بيانات طلب التسجيل
            
        Returns:
            RegistrationRequestResponse: بيانات طلب التسجيل المنشأ
            
        Raises:
            ConflictError: إذا كان هناك طلب معلق لنفس المستخدم
            ValidationError: إذا كانت البيانات غير صالحة
        """
        # تنظيف البيانات
        full_name = sanitize_input(request_data.full_name)
        restaurant_name = sanitize_input(request_data.restaurant_name)
        restaurant_type = sanitize_input(request_data.restaurant_type)
        owner_phone = request_data.owner_phone
        restaurant_phone = request_data.restaurant_phone
        email = sanitize_input(request_data.email) if request_data.email else None
        wilaya = sanitize_input(request_data.wilaya) if request_data.wilaya else None

        logger.info(
            "registration_request_service_create",
            extra={
                "chat_id": request_data.chat_id,
                "restaurant_name": restaurant_name,
            },
        )

        # التحقق من وجود طلب معلق لنفس المستخدم
        existing = await self.repo.get_by_chat_id(
            chat_id=request_data.chat_id,
        )

        if existing and existing.status == "pending":
            raise ConflictError(
                message="يوجد بالفعل طلب تسجيل معلق لهذا المستخدم",
                details={
                    "chat_id": request_data.chat_id,
                    "existing_request_id": existing.id,
                },
            )

        # التحقق من الحد الأقصى للطلبات
        requests_count = len(await self.repo.get_all_by_chat_id(
            chat_id=request_data.chat_id,
            limit=100,
        ))

        if requests_count >= MAX_REQUESTS_PER_CHAT:
            raise ValidationError(
                message=f"تجاوزت الحد الأقصى للطلبات ({MAX_REQUESTS_PER_CHAT})",
                details={
                    "chat_id": request_data.chat_id,
                    "current_count": requests_count,
                    "max_allowed": MAX_REQUESTS_PER_CHAT,
                },
            )

        # التحقق من صحة البريد الإلكتروني
        if email and "@" not in email:
            raise ValidationError(
                message="البريد الإلكتروني غير صالح",
            )

        # إنشاء الطلب
        data: RegistrationData = {
            "chat_id": request_data.chat_id,
            "full_name": full_name,
            "owner_phone": owner_phone,
            "email": email,
            "restaurant_name": restaurant_name,
            "restaurant_type": restaurant_type,
            "restaurant_phone": restaurant_phone,
            "wilaya": wilaya,
            "lat": request_data.lat,
            "lng": request_data.lng,
            "status": "pending",
            "owner_id": None,
        }

        request = await self.repo.create(data=data)

        logger.info(
            "registration_request_created_successfully",
            extra={
                "request_id": request.id,
                "chat_id": request.chat_id,
            },
        )

        return RegistrationRequestResponse.model_validate(request)

    # ==============================================
    # UPDATE
    # ==============================================

    async def update(
        self,
        *,
        request_id: int,
        update_data: RegistrationRequestUpdate,
    ) -> RegistrationRequestResponse:
        """
        تحديث طلب تسجيل.
        
        Args:
            request_id: معرف طلب التسجيل
            update_data: بيانات التحديث
            
        Returns:
            RegistrationRequestResponse: بيانات طلب التسجيل المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "registration_request_service_update",
            extra={
                "request_id": request_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود الطلب
        existing = await self.repo.get_by_id(request_id=request_id)

        if not existing:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        # لا يمكن تحديث طلب معتمد أو مرفوض
        if existing.status in ["approved", "rejected"]:
            raise ValidationError(
                message=f"لا يمكن تحديث طلب بحالة '{existing.status}'",
                details={
                    "request_id": request_id,
                    "status": existing.status,
                },
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف البيانات
        if "full_name" in updates:
            updates["full_name"] = sanitize_input(updates["full_name"])

        if "restaurant_name" in updates:
            updates["restaurant_name"] = sanitize_input(updates["restaurant_name"])

        if "restaurant_type" in updates:
            updates["restaurant_type"] = sanitize_input(updates["restaurant_type"])

        if "email" in updates:
            updates["email"] = sanitize_input(updates["email"])
            if updates["email"] and "@" not in updates["email"]:
                raise ValidationError(
                    message="البريد الإلكتروني غير صالح",
                )

        if "wilaya" in updates:
            updates["wilaya"] = sanitize_input(updates["wilaya"]) if updates["wilaya"] else None

        # تحديث الطلب
        request = await self.repo.update(
            request_id=request_id,
            data=updates,
        )

        if not request:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        logger.info(
            "registration_request_updated_successfully",
            extra={"request_id": request_id},
        )

        return RegistrationRequestResponse.model_validate(request)

    # ==============================================
    # UPDATE STATUS
    # ==============================================

    async def update_status(
        self,
        *,
        request_id: int,
        status_data: RegistrationRequestStatusUpdate,
    ) -> RegistrationRequestResponse:
        """
        تحديث حالة طلب التسجيل.
        
        Args:
            request_id: معرف طلب التسجيل
            status_data: بيانات تحديث الحالة
            
        Returns:
            RegistrationRequestResponse: بيانات طلب التسجيل المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كانت الحالة غير صالحة
        """
        status = status_data.status

        if status not in VALID_REQUEST_STATUSES:
            raise ValidationError(
                message=f"حالة الطلب '{status}' غير صالحة",
                details={
                    "status": status,
                    "valid_statuses": list(VALID_REQUEST_STATUSES),
                },
            )

        logger.info(
            "registration_request_service_update_status",
            extra={
                "request_id": request_id,
                "status": status,
            },
        )

        # التحقق من وجود الطلب
        existing = await self.repo.get_by_id(request_id=request_id)

        if not existing:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        # تحديث الحالة
        if status == "approved":
            request = await self.repo.approve(
                request_id=request_id,
                owner_id=existing.owner_id,
            )
        elif status == "rejected":
            request = await self.repo.reject(request_id=request_id)
        else:
            request = await self.repo.update(
                request_id=request_id,
                data={"status": status},
            )

        if not request:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        logger.info(
            "registration_request_status_updated_successfully",
            extra={
                "request_id": request_id,
                "status": status,
            },
        )

        return RegistrationRequestResponse.model_validate(request)

    # ==============================================
    # APPROVE
    # ==============================================

    async def approve(
        self,
        *,
        request_id: int,
        owner_id: Optional[int] = None,
    ) -> RegistrationRequestResponse:
        """
        الموافقة على طلب التسجيل وإنشاء المالك والمطعم والاشتراك.
        
        Args:
            request_id: معرف طلب التسجيل
            owner_id: معرف المالك (اختياري - إذا كان المالك موجوداً مسبقاً)
            
        Returns:
            RegistrationRequestResponse: بيانات طلب التسجيل المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كان الطلب معتمداً أو مرفوضاً مسبقاً
        """
        logger.info(
            "registration_request_service_approve",
            extra={
                "request_id": request_id,
                "owner_id": owner_id,
            },
        )

        # 1️⃣ الحصول على الطلب
        request = await self.repo.get_by_id(request_id=request_id)

        if not request:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        if request.status == "approved":
            raise ValidationError(
                message=f"طلب التسجيل #{request_id} معتمد بالفعل",
            )

        if request.status == "rejected":
            raise ValidationError(
                message=f"طلب التسجيل #{request_id} مرفوض، لا يمكن اعتماده",
            )

        # 2️⃣ إنشاء المالك (إذا لم يتم توفير owner_id)
        if owner_id is None:
            owner = await self.owner_service.create_owner(
                owner_data={
                    "chat_id": request.chat_id,
                    "full_name": request.full_name,
                    "phone": request.owner_phone,
                    "email": request.email or "",
                    "registration_status": "pending",
                    "trial_used": False,
                },
            )
            owner_id = owner.id

            logger.info(
                "owner_created_during_approval",
                extra={"owner_id": owner_id},
            )

        # 3️⃣ إنشاء المطعم
        restaurant_data = {
            "owner_id": owner_id,
            "name": request.restaurant_name,
            "type": request.restaurant_type,
            "phone": request.restaurant_phone,
            "wilaya": request.wilaya or "",
            "lat": request.lat,
            "lng": request.lng,
            "is_active": True,
        }

        restaurant = await self.restaurant_repo.create(data=restaurant_data)
        restaurant_id = restaurant.id

        logger.info(
            "restaurant_created_during_approval",
            extra={"restaurant_id": restaurant_id},
        )

        # 4️⃣ إنشاء مقاييس المطعم
        # (سيتم إنشاؤها تلقائياً عبر trigger أو يمكن إضافتها يدوياً)

        # 5️⃣ إنشاء اشتراك تجريبي
        subscription = await self.subscription_service.create_trial_subscription(
            owner_id=owner_id,
            restaurant_id=restaurant_id,
        )
        subscription_id = subscription.id if subscription else None

        logger.info(
            "subscription_created_during_approval",
            extra={"subscription_id": subscription_id},
        )

        # 6️⃣ تحديث المالك إلى approved
        await self.owner_service.approve_owner(owner_id=owner_id)

        # 7️⃣ تحديث طلب التسجيل إلى approved
        updated_request = await self.repo.approve(
            request_id=request_id,
            owner_id=owner_id,
        )

        if not updated_request:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        logger.info(
            "registration_approved_successfully",
            extra={
                "request_id": request_id,
                "owner_id": owner_id,
                "restaurant_id": restaurant_id,
                "subscription_id": subscription_id,
            },
        )

        return RegistrationRequestResponse.model_validate(updated_request)

    # ==============================================
    # REJECT
    # ==============================================

    async def reject(
        self,
        *,
        request_id: int,
    ) -> RegistrationRequestResponse:
        """
        رفض طلب التسجيل.
        
        Args:
            request_id: معرف طلب التسجيل
            
        Returns:
            RegistrationRequestResponse: بيانات طلب التسجيل المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كان الطلب معتمداً أو مرفوضاً مسبقاً
        """
        logger.info(
            "registration_request_service_reject",
            extra={"request_id": request_id},
        )

        # التحقق من وجود الطلب
        request = await self.repo.get_by_id(request_id=request_id)

        if not request:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        if request.status == "approved":
            raise ValidationError(
                message=f"طلب التسجيل #{request_id} معتمد، لا يمكن رفضه",
            )

        if request.status == "rejected":
            raise ValidationError(
                message=f"طلب التسجيل #{request_id} مرفوض بالفعل",
            )

        request = await self.repo.reject(request_id=request_id)

        if not request:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        logger.info(
            "registration_rejected_successfully",
            extra={"request_id": request_id},
        )

        return RegistrationRequestResponse.model_validate(request)

    # ==============================================
    # DELETE
    # ==============================================

    async def delete(
        self,
        *,
        request_id: int,
    ) -> None:
        """
        حذف طلب تسجيل.
        
        Args:
            request_id: معرف طلب التسجيل
            
        Raises:
            NotFoundError: إذا لم يتم العثور على الطلب
            ValidationError: إذا كان الطلب معتمداً
        """
        logger.info(
            "registration_request_service_delete",
            extra={"request_id": request_id},
        )

        # التحقق من وجود الطلب
        request = await self.repo.get_by_id(request_id=request_id)

        if not request:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        # لا يمكن حذف طلب معتمد
        if request.status == "approved":
            raise ValidationError(
                message=f"لا يمكن حذف طلب تسجيل معتمد",
                details={
                    "request_id": request_id,
                    "status": request.status,
                },
            )

        deleted = await self.repo.delete(request_id=request_id)

        if not deleted:
            raise NotFoundError(
                message=f"طلب التسجيل بـ ID '{request_id}' غير موجود",
            )

        logger.info(
            "registration_request_deleted_successfully",
            extra={"request_id": request_id},
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# APPROVE REGISTRATION (COMPATIBILITY)
# ==============================================

async def approve_registration(
    *,
    request_id: int,
    session: AsyncSession,
) -> RegistrationResult:
    """
    الموافقة على طلب التسجيل (دالة متوافقة مع الإصدار القديم).
    
    Args:
        request_id: معرف طلب التسجيل
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        RegistrationResult: نتائج الموافقة (owner_id, restaurant_id, subscription_id)
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كان الطلب معتمداً أو مرفوضاً
    """
    service = RegistrationRequestService(session=session)

    request = await service.approve(request_id=request_id)

    # الحصول على البيانات المطلوبة
    owner_id = request.id

    # الحصول على المطعم
    restaurants = await service.restaurant_repo.get_by_owner_id(owner_id=owner_id)
    restaurant_id = restaurants[0].id if restaurants else None

    # الحصول على الاشتراك
    if restaurant_id:
        subscription = await service.subscription_service.get_active_by_restaurant(
            restaurant_id=restaurant_id,
        )
        subscription_id = subscription.id if subscription else None
    else:
        subscription_id = None

    return {
        "owner_id": owner_id,
        "restaurant_id": restaurant_id,
        "subscription_id": subscription_id,
    }


# ==============================================
# REJECT REGISTRATION (COMPATIBILITY)
# ==============================================

async def reject_registration(
    *,
    request_id: int,
    session: AsyncSession,
) -> None:
    """
    رفض طلب التسجيل (دالة متوافقة مع الإصدار القديم).
    
    Args:
        request_id: معرف طلب التسجيل
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على الطلب
        ValidationError: إذا كان الطلب معتمداً أو مرفوضاً
    """
    service = RegistrationRequestService(session=session)

    await service.reject(request_id=request_id)


# ==============================================
# GET REGISTRATION PREVIEW (COMPATIBILITY)
# ==============================================

async def get_registration_preview(
    *,
    request_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على معاينة طلب التسجيل (دالة متوافقة مع الإصدار القديم).
    
    Args:
        request_id: معرف طلب التسجيل
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات الطلب أو None
    """
    service = RegistrationRequestService(session=session)

    try:
        request = await service.get_by_id(request_id=request_id)
        return request.model_dump()
    except NotFoundError:
        return None


# ==============================================
# GET PENDING REQUESTS (COMPATIBILITY)
# ==============================================

async def get_pending_requests(
    *,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على طلبات التسجيل المعلقة (دالة متوافقة مع الإصدار القديم).
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        List[Dict[str, Any]]: قائمة طلبات التسجيل المعلقة
    """
    service = RegistrationRequestService(session=session)

    requests = await service.get_pending(
        skip=skip,
        limit=limit,
    )

    return [req.model_dump() for req in requests]


# ==============================================
# GET REGISTRATION REQUEST BY ID (COMPATIBILITY)
# ==============================================

async def get_registration_request_by_id(
    *,
    request_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على طلب تسجيل بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        request_id: معرف طلب التسجيل
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات الطلب أو None
    """
    service = RegistrationRequestService(session=session)

    try:
        request = await service.get_by_id(request_id=request_id)
        return request.model_dump()
    except NotFoundError:
        return None