# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 👤 OWNER SERVICE
# Business Logic Layer
# منطق الأعمال للمالكين
# يدير عمليات إنشاء واستعراض وتحديث وحذف المالكين
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

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
from app.models.owner import Owner
from app.repositories.owner_repo import OwnerRepository

# ✅ استيراد المخططات
from app.schemas.owner import (
    OwnerCreate,
    OwnerResponse,
    OwnerUpdate,
    OwnerStatusUpdate,
)


# ==============================================
# 🧩 CONSTANTS
# ==============================================

VALID_REGISTRATION_STATUSES = {"pending", "approved", "rejected"}


# ==============================================
# 🧩 TYPES
# ==============================================

OwnerData = Dict[str, Any]
OwnerUpdateData = Dict[str, Any]
OwnerList = List[Owner]


# ==============================================
# 👤 OWNER SERVICE
# ==============================================

class OwnerService:
    """
    خدمة المالكين - تدير منطق الأعمال للمالكين.
    
    مسؤولة عن:
        - إنشاء وإدارة المالكين
        - اعتماد ورفض المالكين
        - إدارة الفترة التجريبية
        - البحث والتصفية
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع المالكين
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة المالكين.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = OwnerRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET OWNER BY ID
    # ==============================================

    async def get_owner_by_id(
        self,
        *,
        owner_id: int,
    ) -> OwnerResponse:
        """
        الحصول على مالك بالمعرف.
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            OwnerResponse: بيانات المالك
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
        """
        logger.info(
            "owner_service_get_by_id",
            extra={"owner_id": owner_id},
        )

        owner = await self.repo.get_by_id(
            owner_id=owner_id,
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        return OwnerResponse.model_validate(owner)

    # ==============================================
    # GET OWNER BY CHAT ID
    # ==============================================

    async def get_owner_by_chat_id(
        self,
        *,
        chat_id: int,
    ) -> Optional[OwnerResponse]:
        """
        الحصول على مالك بواسطة chat_id.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            Optional[OwnerResponse]: بيانات المالك أو None
        """
        logger.info(
            "owner_service_get_by_chat_id",
            extra={"chat_id": chat_id},
        )

        owner = await self.repo.get_by_chat_id(
            chat_id=chat_id,
        )

        if not owner:
            return None

        return OwnerResponse.model_validate(owner)

    # ==============================================
    # GET ALL OWNERS
    # ==============================================

    async def get_all_owners(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        only_approved: bool = False,
    ) -> List[OwnerResponse]:
        """
        الحصول على جميع المالكين.
        
        Args:
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            only_approved: جلب المالكين المعتمدين فقط
            
        Returns:
            List[OwnerResponse]: قائمة المالكين
        """
        logger.info(
            "owner_service_get_all",
            extra={
                "skip": skip,
                "limit": limit,
                "only_approved": only_approved,
            },
        )

        filters = {}

        if only_approved:
            filters["registration_status"] = "approved"

        owners = await self.repo.get_all(
            skip=skip,
            limit=limit,
            filters=filters,
            order_by="created_at",
            descending=True,
        )

        return [OwnerResponse.model_validate(owner) for owner in owners]

    # ==============================================
    # GET OWNERS BY STATUS
    # ==============================================

    async def get_owners_by_status(
        self,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OwnerResponse]:
        """
        الحصول على المالكين حسب حالة التسجيل.
        
        Args:
            status: حالة التسجيل (pending, approved, rejected)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[OwnerResponse]: قائمة المالكين
            
        Raises:
            ValidationError: إذا كانت الحالة غير صالحة
        """
        if status not in VALID_REGISTRATION_STATUSES:
            raise ValidationError(
                message=f"حالة التسجيل '{status}' غير صالحة",
                details={
                    "status": status,
                    "valid_statuses": list(VALID_REGISTRATION_STATUSES),
                },
            )

        logger.info(
            "owner_service_get_by_status",
            extra={
                "status": status,
                "skip": skip,
                "limit": limit,
            },
        )

        owners = await self.repo.get_all(
            skip=skip,
            limit=limit,
            filters={"registration_status": status},
            order_by="created_at",
            descending=True,
        )

        return [OwnerResponse.model_validate(owner) for owner in owners]

    # ==============================================
    # SEARCH OWNERS
    # ==============================================

    async def search_owners(
        self,
        *,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OwnerResponse]:
        """
        البحث عن المالكين.
        
        Args:
            query: نص البحث (full_name, phone, email)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[OwnerResponse]: قائمة المالكين
        """
        clean_query = sanitize_input(query)

        logger.info(
            "owner_service_search",
            extra={
                "query": clean_query,
                "skip": skip,
                "limit": limit,
            },
        )

        owners = await self.repo.search(
            query=clean_query,
            skip=skip,
            limit=limit,
        )

        return [OwnerResponse.model_validate(owner) for owner in owners]

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # COUNT OWNERS
    # ==============================================

    async def count_owners(
        self,
        *,
        status: Optional[str] = None,
    ) -> int:
        """
        حساب عدد المالكين.
        
        Args:
            status: حالة التسجيل (اختياري)
            
        Returns:
            int: عدد المالكين
        """
        filters = {}

        if status:
            if status not in VALID_REGISTRATION_STATUSES:
                raise ValidationError(
                    message=f"حالة التسجيل '{status}' غير صالحة",
                    details={
                        "status": status,
                        "valid_statuses": list(VALID_REGISTRATION_STATUSES),
                    },
                )
            filters["registration_status"] = status

        return await self.repo.count(filters=filters)

    # ==============================================
    # GET OWNER STATISTICS
    # ==============================================

    async def get_owner_statistics(
        self,
    ) -> Dict[str, int]:
        """
        الحصول على إحصائيات المالكين.
        
        Returns:
            Dict[str, int]: إحصائيات المالكين
        """
        logger.info("owner_service_get_statistics")

        total = await self.count_owners()
        pending = await self.count_owners(status="pending")
        approved = await self.count_owners(status="approved")
        rejected = await self.count_owners(status="rejected")

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        }

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE OWNER
    # ==============================================

    async def create_owner(
        self,
        *,
        owner_data: OwnerCreate,
    ) -> OwnerResponse:
        """
        إنشاء مالك جديد.
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_data: بيانات المالك
            
        Returns:
            OwnerResponse: بيانات المالك المنشأ
            
        Raises:
            ConflictError: إذا كان chat_id موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صالحة
        """
        # تنظيف البيانات
        full_name = sanitize_input(owner_data.full_name)
        phone = sanitize_input(owner_data.phone) if owner_data.phone else None
        email = sanitize_input(owner_data.email) if owner_data.email else None

        logger.info(
            "owner_service_create",
            extra={
                "chat_id": owner_data.chat_id,
                "full_name": full_name,
            },
        )

        # التحقق من عدم وجود chat_id مكرر
        existing = await self.repo.get_by_chat_id(
            chat_id=owner_data.chat_id,
        )

        if existing:
            raise ConflictError(
                message=f"المالك بـ chat_id '{owner_data.chat_id}' موجود مسبقاً",
            )

        # التحقق من صحة البريد الإلكتروني
        if email and "@" not in email:
            raise ValidationError(
                message="البريد الإلكتروني غير صالح",
            )

        # تعيين القيم الافتراضية
        data: OwnerData = {
            "chat_id": owner_data.chat_id,
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "registration_status": owner_data.registration_status or "pending",
            "trial_used": owner_data.trial_used or False,
        }

        try:
            # ✅ base.py يقوم بـ commit() و refresh()
            owner = await self.repo.create(data=data)
            
            # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

            logger.info(
                "owner_created_successfully",
                extra={
                    "owner_id": owner.id,
                    "chat_id": owner.chat_id,
                },
            )

            return OwnerResponse.model_validate(owner)

        except IntegrityError as e:
            logger.warning(
                "owner_service_create_integrity_error",
                extra={
                    "chat_id": owner_data.chat_id,
                    "error": str(e),
                },
            )
            raise ConflictError(
                message=f"المالك بـ chat_id '{owner_data.chat_id}' موجود مسبقاً",
            )
        except Exception as e:
            logger.exception(
                "owner_service_create_error",
                extra={
                    "chat_id": owner_data.chat_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # UPDATE OWNER
    # ==============================================

    async def update_owner(
        self,
        *,
        owner_id: int,
        update_data: OwnerUpdate,
    ) -> OwnerResponse:
        """
        تحديث مالك.
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_id: معرف المالك
            update_data: بيانات التحديث
            
        Returns:
            OwnerResponse: بيانات المالك المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
            ConflictError: إذا كان chat_id موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "owner_service_update",
            extra={
                "owner_id": owner_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود المالك
        existing = await self.repo.get_by_id(owner_id=owner_id)

        if not existing:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف البيانات
        if "full_name" in updates:
            updates["full_name"] = sanitize_input(updates["full_name"])

        if "phone" in updates:
            updates["phone"] = sanitize_input(updates["phone"])

        if "email" in updates:
            updates["email"] = sanitize_input(updates["email"])

            # التحقق من صحة البريد الإلكتروني
            if updates["email"] and "@" not in updates["email"]:
                raise ValidationError(
                    message="البريد الإلكتروني غير صالح",
                )

        # ✅ base.py يقوم بـ commit() و refresh()
        owner = await self.repo.update(
            owner_id=owner_id,
            data=updates,
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

        logger.info(
            "owner_updated_successfully",
            extra={
                "owner_id": owner_id,
                "updated_fields": list(updates.keys()),
            },
        )

        return OwnerResponse.model_validate(owner)

    # ==============================================
    # UPDATE OWNER STATUS
    # ==============================================

    async def update_owner_status(
        self,
        *,
        owner_id: int,
        status_data: OwnerStatusUpdate,
    ) -> OwnerResponse:
        """
        تحديث حالة المالك.
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_id: معرف المالك
            status_data: بيانات تحديث الحالة
            
        Returns:
            OwnerResponse: بيانات المالك المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
            ValidationError: إذا كانت الحالة غير صالحة
        """
        status = status_data.registration_status

        if status not in VALID_REGISTRATION_STATUSES:
            raise ValidationError(
                message=f"حالة التسجيل '{status}' غير صالحة",
                details={
                    "status": status,
                    "valid_statuses": list(VALID_REGISTRATION_STATUSES),
                },
            )

        logger.info(
            "owner_service_update_status",
            extra={
                "owner_id": owner_id,
                "status": status,
            },
        )

        # ✅ base.py يقوم بـ commit() و refresh()
        owner = await self.repo.update(
            owner_id=owner_id,
            data={"registration_status": status},
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

        logger.info(
            "owner_status_updated_successfully",
            extra={
                "owner_id": owner_id,
                "status": status,
            },
        )

        return OwnerResponse.model_validate(owner)

    # ==============================================
    # APPROVE OWNER
    # ==============================================

    async def approve_owner(
        self,
        *,
        owner_id: int,
    ) -> OwnerResponse:
        """
        اعتماد مالك (تغيير الحالة إلى approved).
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            OwnerResponse: بيانات المالك المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
        """
        logger.info(
            "owner_service_approve",
            extra={"owner_id": owner_id},
        )

        # ✅ base.py يقوم بـ commit() و refresh()
        owner = await self.repo.update(
            owner_id=owner_id,
            data={"registration_status": "approved"},
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

        logger.info(
            "owner_approved_successfully",
            extra={"owner_id": owner_id},
        )

        return OwnerResponse.model_validate(owner)

    # ==============================================
    # REJECT OWNER
    # ==============================================

    async def reject_owner(
        self,
        *,
        owner_id: int,
    ) -> OwnerResponse:
        """
        رفض مالك (تغيير الحالة إلى rejected).
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            OwnerResponse: بيانات المالك المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
        """
        logger.info(
            "owner_service_reject",
            extra={"owner_id": owner_id},
        )

        # ✅ base.py يقوم بـ commit() و refresh()
        owner = await self.repo.update(
            owner_id=owner_id,
            data={"registration_status": "rejected"},
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

        logger.info(
            "owner_rejected_successfully",
            extra={"owner_id": owner_id},
        )

        return OwnerResponse.model_validate(owner)

    # ==============================================
    # SET OWNER PENDING
    # ==============================================

    async def set_owner_pending(
        self,
        *,
        owner_id: int,
    ) -> OwnerResponse:
        """
        تعيين حالة المالك إلى pending.
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            OwnerResponse: بيانات المالك المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
        """
        logger.info(
            "owner_service_set_pending",
            extra={"owner_id": owner_id},
        )

        # ✅ base.py يقوم بـ commit() و refresh()
        owner = await self.repo.update(
            owner_id=owner_id,
            data={"registration_status": "pending"},
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

        logger.info(
            "owner_set_pending_successfully",
            extra={"owner_id": owner_id},
        )

        return OwnerResponse.model_validate(owner)

    # ==============================================
    # TOGGLE TRIAL USED
    # ==============================================

    async def toggle_trial_used(
        self,
        *,
        owner_id: int,
        trial_used: bool,
    ) -> OwnerResponse:
        """
        تحديث حالة استخدام الفترة التجريبية.
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_id: معرف المالك
            trial_used: حالة الاستخدام
            
        Returns:
            OwnerResponse: بيانات المالك المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
        """
        logger.info(
            "owner_service_toggle_trial",
            extra={
                "owner_id": owner_id,
                "trial_used": trial_used,
            },
        )

        # ✅ base.py يقوم بـ commit() و refresh()
        owner = await self.repo.update(
            owner_id=owner_id,
            data={"trial_used": trial_used},
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

        logger.info(
            "owner_trial_toggled_successfully",
            extra={
                "owner_id": owner_id,
                "trial_used": trial_used,
            },
        )

        return OwnerResponse.model_validate(owner)

    # ==========================================
    # 🎁 TRIAL
    # ==========================================

    # ==============================================
    # CAN USE TRIAL
    # ==============================================

    async def can_use_trial(
        self,
        *,
        owner_id: int,
    ) -> bool:
        """
        التحقق من إمكانية استخدام الفترة التجريبية.
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            bool: True إذا كان يمكن استخدام الفترة التجريبية
        """
        owner = await self.repo.get_by_id(owner_id=owner_id)

        if not owner:
            return False

        # يمكن استخدام الفترة التجريبية إذا:
        # 1. لم يتم استخدامها من قبل
        # 2. المالك معتمد (approved)
        return not owner.trial_used and owner.registration_status == "approved"

    # ==============================================
    # ACTIVATE TRIAL
    # ==============================================

    async def activate_trial(
        self,
        *,
        owner_id: int,
    ) -> OwnerResponse:
        """
        تفعيل استخدام الفترة التجريبية.
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_id: معرف المالك
            
        Returns:
            OwnerResponse: بيانات المالك المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
            ValidationError: إذا كان المالك غير مؤهل للفترة التجريبية
        """
        logger.info(
            "owner_service_activate_trial",
            extra={"owner_id": owner_id},
        )

        # التحقق من إمكانية استخدام الفترة التجريبية
        can_use = await self.can_use_trial(owner_id=owner_id)

        if not can_use:
            owner = await self.repo.get_by_id(owner_id=owner_id)

            if not owner:
                raise NotFoundError(
                    message=f"المالك بـ ID '{owner_id}' غير موجود",
                )

            if owner.trial_used:
                raise ValidationError(
                    message="تم استخدام الفترة التجريبية بالفعل",
                )

            if owner.registration_status != "approved":
                raise ValidationError(
                    message="المالك غير معتمد، لا يمكن تفعيل الفترة التجريبية",
                )

        # ✅ base.py يقوم بـ commit() و refresh()
        owner = await self.repo.update(
            owner_id=owner_id,
            data={"trial_used": True},
        )

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

        logger.info(
            "owner_trial_activated_successfully",
            extra={"owner_id": owner_id},
        )

        return OwnerResponse.model_validate(owner)

    # ==========================================
    # 🗑️ DELETE
    # ==========================================

    # ==============================================
    # DELETE OWNER
    # ==============================================

    async def delete_owner(
        self,
        *,
        owner_id: int,
    ) -> None:
        """
        حذف مالك.
        
        ✅ التصحيح: إزالة commit() لأن base.py يقوم بها
        
        Args:
            owner_id: معرف المالك
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المالك
            ValidationError: إذا كان المالك مرتبطاً بمطاعم
        """
        logger.info(
            "owner_service_delete",
            extra={"owner_id": owner_id},
        )

        # التحقق من وجود المالك
        owner = await self.repo.get_by_id(owner_id=owner_id)

        if not owner:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # التحقق من عدم وجود مطاعم مرتبطة
        restaurants_count = await self.repo.count_restaurants(owner_id=owner_id)

        if restaurants_count > 0:
            raise ValidationError(
                message="لا يمكن حذف المالك لأنه يمتلك مطاعم",
                details={
                    "owner_id": owner_id,
                    "restaurants_count": restaurants_count,
                },
            )

        # ✅ base.py يقوم بـ commit()
        deleted = await self.repo.delete(owner_id=owner_id)

        if not deleted:
            raise NotFoundError(
                message=f"المالك بـ ID '{owner_id}' غير موجود",
            )

        # ✅ لا داعي لـ commit() هنا لأن base.py يقوم بها

        logger.info(
            "owner_deleted_successfully",
            extra={"owner_id": owner_id},
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# GET OR CREATE OWNER (COMPATIBILITY)
# ==============================================

async def get_or_create_owner(
    *,
    chat_id: int,
    full_name: str,
    phone: str,
    email: str,
    session: AsyncSession,
) -> int:
    """
    الحصول على مالك أو إنشاؤه (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        full_name: الاسم الكامل
        phone: رقم الهاتف
        email: البريد الإلكتروني
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف المالك
    """
    service = OwnerService(session=session)

    # البحث عن مالك موجود
    owner = await service.get_owner_by_chat_id(chat_id=chat_id)

    if owner:
        logger.info(
            "owner_already_exists",
            extra={
                "owner_id": owner.id,
                "chat_id": chat_id,
            },
        )
        return owner.id

    # إنشاء مالك جديد
    owner_data = OwnerCreate(
        chat_id=chat_id,
        full_name=full_name,
        phone=phone,
        email=email,
        registration_status="pending",
        trial_used=False,
    )

    owner = await service.create_owner(owner_data=owner_data)

    logger.info(
        "owner_created_from_service",
        extra={
            "owner_id": owner.id,
            "chat_id": chat_id,
        },
    )

    return owner.id


# ==============================================
# CAN USE TRIAL (COMPATIBILITY)
# ==============================================

async def can_use_trial(
    *,
    owner_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من إمكانية استخدام الفترة التجريبية.
    
    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        bool: True إذا كان يمكن استخدام الفترة التجريبية
    """
    service = OwnerService(session=session)

    return await service.can_use_trial(owner_id=owner_id)


# ==============================================
# ACTIVATE TRIAL USAGE (COMPATIBILITY)
# ==============================================

async def activate_trial_usage(
    *,
    owner_id: int,
    session: AsyncSession,
) -> None:
    """
    تفعيل استخدام الفترة التجريبية.
    
    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = OwnerService(session=session)

    await service.activate_trial(owner_id=owner_id)


# ==============================================
# APPROVE OWNER (COMPATIBILITY)
# ==============================================

async def approve_owner(
    *,
    owner_id: int,
    session: AsyncSession,
) -> None:
    """
    اعتماد مالك.
    
    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = OwnerService(session=session)

    await service.approve_owner(owner_id=owner_id)


# ==============================================
# REJECT OWNER (COMPATIBILITY)
# ==============================================

async def reject_owner(
    *,
    owner_id: int,
    session: AsyncSession,
) -> None:
    """
    رفض مالك.
    
    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = OwnerService(session=session)

    await service.reject_owner(owner_id=owner_id)


# ==============================================
# SET OWNER PENDING (COMPATIBILITY)
# ==============================================

async def set_owner_pending(
    *,
    owner_id: int,
    session: AsyncSession,
) -> None:
    """
    تعيين حالة المالك إلى pending.
    
    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
    """
    service = OwnerService(session=session)

    await service.set_owner_pending(owner_id=owner_id)


# ==============================================
# GET OWNER (COMPATIBILITY)
# ==============================================

async def get_owner(
    *,
    owner_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مالك بالمعرف (دالة متوافقة مع الإصدار القديم).
    
    Args:
        owner_id: معرف المالك
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات المالك أو None
    """
    service = OwnerService(session=session)

    try:
        owner = await service.get_owner_by_id(owner_id=owner_id)
        return owner.model_dump()
    except NotFoundError:
        return None


# ==============================================
# GET OWNER BY CHAT ID (COMPATIBILITY)
# ==============================================

async def get_owner_by_chat_id(
    *,
    chat_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مالك بواسطة chat_id (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات المالك أو None
    """
    service = OwnerService(session=session)

    owner = await service.get_owner_by_chat_id(chat_id=chat_id)

    if not owner:
        return None

    return owner.model_dump()


# ==============================================
# GET ALL OWNERS (COMPATIBILITY)
# ==============================================

async def get_all_owners(
    *,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    only_approved: bool = False,
) -> List[Dict[str, Any]]:
    """
    الحصول على جميع المالكين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        only_approved: جلب المالكين المعتمدين فقط
        
    Returns:
        List[Dict[str, Any]]: قائمة المالكين
    """
    service = OwnerService(session=session)

    owners = await service.get_all_owners(
        skip=skip,
        limit=limit,
        only_approved=only_approved,
    )

    return [owner.model_dump() for owner in owners]


# ==============================================
# GET OWNERS BY STATUS (COMPATIBILITY)
# ==============================================

async def get_owners_by_status(
    *,
    status: str,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    الحصول على المالكين حسب حالة التسجيل (دالة متوافقة مع الإصدار القديم).
    
    Args:
        status: حالة التسجيل (pending, approved, rejected)
        session: جلسة قاعدة البيانات غير المتزامنة
        skip: عدد السجلات للتخطي
        limit: الحد الأقصى للسجلات
        
    Returns:
        List[Dict[str, Any]]: قائمة المالكين
    """
    service = OwnerService(session=session)

    owners = await service.get_owners_by_status(
        status=status,
        skip=skip,
        limit=limit,
    )

    return [owner.model_dump() for owner in owners]