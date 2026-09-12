# ==============================================
# 👤 USER SERVICE
# منطق الأعمال للمستخدمين
#
# إنشاء مستخدم
# قراءة مستخدم
# تحديث مستخدم
# إدارة الموافقة (Consent)
# البحث عن مستخدمين
# إحصائيات المستخدمين
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
from app.models.user import User
from app.repositories.user_repo import UserRepository

# ✅ استيراد المخططات
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserConsentUpdate,
    UserListResponse,
    UserSummary,
    UserSearch,
)


# ==============================================
# 🧩 TYPES
# ==============================================

UserData = Dict[str, Any]
UserUpdateData = Dict[str, Any]
UserList = List[User]
UserStats = Dict[str, Any]


# ==============================================
# 👤 USER SERVICE
# ==============================================


class UserService:
    """
    خدمة المستخدمين - تدير منطق الأعمال للمستخدمين.
    
    مسؤولة عن:
        - إنشاء وإدارة المستخدمين
        - إدارة موافقة المستخدم (Consent)
        - البحث عن المستخدمين
        - إحصائيات المستخدمين
    
    Attributes:
        session: جلسة قاعدة البيانات غير المتزامنة
        repo: مستودع المستخدمين
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة خدمة المستخدمين.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        self.session = session
        self.repo = UserRepository(session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY ID
    # ==============================================

    async def get_by_id(
        self,
        *,
        user_id: int,
    ) -> UserResponse:
        """
        الحصول على مستخدم بالمعرف.
        
        Args:
            user_id: معرف المستخدم
            
        Returns:
            UserResponse: بيانات المستخدم
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المستخدم
        """
        logger.info(
            "user_service_get_by_id",
            extra={"user_id": user_id},
        )

        user = await self.repo.get_by_id(
            id=user_id,
        )

        if not user:
            raise NotFoundError(
                message=f"المستخدم بـ ID '{user_id}' غير موجود",
            )

        return UserResponse.model_validate(user)

    # ==============================================
    # GET BY CHAT ID
    # ==============================================

    async def get_by_chat_id(
        self,
        *,
        chat_id: int,
    ) -> Optional[UserResponse]:
        """
        الحصول على مستخدم بواسطة chat_id.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            Optional[UserResponse]: بيانات المستخدم أو None
        """
        logger.info(
            "user_service_get_by_chat_id",
            extra={"chat_id": chat_id},
        )

        user = await self.repo.get_by_chat_id(
            chat_id=chat_id,
        )

        if not user:
            return None

        return UserResponse.model_validate(user)

    # ==============================================
    # GET BY PHONE
    # ==============================================

    async def get_by_phone(
        self,
        *,
        phone: str,
    ) -> Optional[UserResponse]:
        """
        الحصول على مستخدم بواسطة رقم الهاتف.
        
        Args:
            phone: رقم الهاتف
            
        Returns:
            Optional[UserResponse]: بيانات المستخدم أو None
        """
        clean_phone = sanitize_input(phone)

        logger.info(
            "user_service_get_by_phone",
            extra={"phone": clean_phone},
        )

        user = await self.repo.get_by_phone(
            phone=clean_phone,
        )

        if not user:
            return None

        return UserResponse.model_validate(user)

    # ==============================================
    # SEARCH BY NAME
    # ==============================================

    async def search_by_name(
        self,
        *,
        name: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UserResponse]:
        """
        البحث عن مستخدمين بواسطة الاسم.
        
        Args:
            name: اسم العميل
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[UserResponse]: قائمة المستخدمين
        """
        clean_name = sanitize_input(name)

        logger.info(
            "user_service_search_by_name",
            extra={
                "search_name": clean_name,
                "skip": skip,
                "limit": limit,
            },
        )

        users = await self.repo.get_by_name(
            name=clean_name,
            skip=skip,
            limit=limit,
        )

        return [UserResponse.model_validate(user) for user in users]

    # ==============================================
    # SEARCH
    # ==============================================

    async def search(
        self,
        *,
        search_params: UserSearch,
    ) -> UserListResponse:
        """
        البحث عن مستخدمين (الاسم أو رقم الهاتف).
        
        Args:
            search_params: معايير البحث
            
        Returns:
            UserListResponse: قائمة المستخدمين مع الإحصائيات
        """
        clean_query = sanitize_input(search_params.query)

        logger.info(
            "user_service_search",
            extra={
                "query": clean_query,
                "skip": search_params.skip,
                "limit": search_params.limit,
            },
        )

        users = await self.repo.search(
            query=clean_query,
            skip=search_params.skip,
            limit=search_params.limit,
        )

        total = len(users)

        return UserListResponse(
            items=[UserResponse.model_validate(user) for user in users],
            total=total,
            skip=search_params.skip,
            limit=search_params.limit,
        )

    # ==============================================
    # GET BY CONSENT
    # ==============================================

    async def get_by_consent(
        self,
        *,
        has_consent: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UserResponse]:
        """
        الحصول على المستخدمين حسب حالة الموافقة.
        
        Args:
            has_consent: حالة الموافقة
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            List[UserResponse]: قائمة المستخدمين
        """
        logger.info(
            "user_service_get_by_consent",
            extra={
                "has_consent": has_consent,
                "skip": skip,
                "limit": limit,
            },
        )

        users = await self.repo.get_by_consent(
            has_consent=has_consent,
            skip=skip,
            limit=limit,
        )

        return [UserResponse.model_validate(user) for user in users]

    # ==========================================
    # ✅ CONSENT
    # ==========================================

    # ==============================================
    # HAS CONSENT
    # ==============================================

    async def has_consent(
        self,
        *,
        chat_id: int,
    ) -> bool:
        """
        التحقق مما إذا كان المستخدم قد أعطى موافقته.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            bool: True إذا كان لديه موافقة، False إذا لم يكن
        """
        logger.info(
            "user_service_has_consent",
            extra={"chat_id": chat_id},
        )

        return await self.repo.has_consent(
            chat_id=chat_id,
        )

    # ==============================================
    # UPDATE CONSENT
    # ==============================================

    async def update_consent(
        self,
        *,
        chat_id: int,
        consent_data: UserConsentUpdate,
    ) -> UserResponse:
        """
        تحديث موافقة المستخدم.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            consent_data: بيانات الموافقة
            
        Returns:
            UserResponse: بيانات المستخدم المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المستخدم
        """
        logger.info(
            "user_service_update_consent",
            extra={
                "chat_id": chat_id,
                "consent": consent_data.consent,
            },
        )

        user = await self.repo.get_by_chat_id(
            chat_id=chat_id,
        )

        if not user:
            # إذا كان المستخدم غير موجود ونعطي موافقة، نقوم بإنشائه
            if consent_data.consent:
                user = await self.repo.give_consent(chat_id=chat_id)
                return UserResponse.model_validate(user)
            else:
                raise NotFoundError(
                    message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
                )

        # تحديث الموافقة
        if consent_data.consent:
            user = await self.repo.give_consent(chat_id=chat_id)
        else:
            user = await self.repo.revoke_consent(chat_id=chat_id)

        if not user:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        logger.info(
            "user_consent_updated_successfully",
            extra={
                "user_id": user.id,
                "chat_id": chat_id,
                "consent": consent_data.consent,
            },
        )

        return UserResponse.model_validate(user)

    # ==============================================
    # GIVE CONSENT
    # ==============================================

    async def give_consent(
        self,
        *,
        chat_id: int,
    ) -> UserResponse:
        """
        منح الموافقة للمستخدم (إنشاء المستخدم إذا لم يكن موجوداً).
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            UserResponse: بيانات المستخدم المنشأ أو المحدث
        """
        logger.info(
            "user_service_give_consent",
            extra={"chat_id": chat_id},
        )

        user = await self.repo.give_consent(
            chat_id=chat_id,
        )

        logger.info(
            "user_consent_given_successfully",
            extra={
                "user_id": user.id,
                "chat_id": chat_id,
            },
        )

        return UserResponse.model_validate(user)

    # ==============================================
    # REVOKE CONSENT
    # ==============================================

    async def revoke_consent(
        self,
        *,
        chat_id: int,
    ) -> UserResponse:
        """
        إلغاء موافقة المستخدم.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Returns:
            UserResponse: بيانات المستخدم المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المستخدم
        """
        logger.info(
            "user_service_revoke_consent",
            extra={"chat_id": chat_id},
        )

        user = await self.repo.revoke_consent(
            chat_id=chat_id,
        )

        if not user:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        logger.info(
            "user_consent_revoked_successfully",
            extra={
                "user_id": user.id,
                "chat_id": chat_id,
            },
        )

        return UserResponse.model_validate(user)

    # ==========================================
    # ✏️ MUTATIONS
    # ==========================================

    # ==============================================
    # CREATE USER
    # ==============================================

    async def create_user(
        self,
        *,
        user_data: UserCreate,
    ) -> UserResponse:
        """
        إنشاء مستخدم جديد.
        
        Args:
            user_data: بيانات المستخدم
            
        Returns:
            UserResponse: بيانات المستخدم المنشأ
            
        Raises:
            ConflictError: إذا كان chat_id موجوداً مسبقاً
            ValidationError: إذا كانت البيانات غير صالحة
        """
        logger.info(
            "user_service_create",
            extra={
                "chat_id": user_data.chat_id,
                "customer_name": user_data.customer_name,
            },
        )

        # التحقق من عدم وجود مستخدم بنفس chat_id
        existing = await self.repo.get_by_chat_id(
            chat_id=user_data.chat_id,
        )

        if existing:
            raise ConflictError(
                message=f"المستخدم بـ chat_id '{user_data.chat_id}' موجود مسبقاً",
            )

        # تنظيف البيانات
        customer_name = sanitize_input(user_data.customer_name) if user_data.customer_name else None
        customer_phone = sanitize_input(user_data.customer_phone) if user_data.customer_phone else None

        # إنشاء المستخدم
        data: UserData = {
            "chat_id": user_data.chat_id,
            "consent": user_data.consent or False,
        }

        if customer_name is not None:
            data["customer_name"] = customer_name

        if customer_phone is not None:
            data["customer_phone"] = customer_phone

        user = await self.repo.create(data=data)

        logger.info(
            "user_created_successfully",
            extra={
                "user_id": user.id,
                "chat_id": user_data.chat_id,
            },
        )

        return UserResponse.model_validate(user)

    # ==============================================
    # UPDATE USER
    # ==============================================

    async def update_user(
        self,
        *,
        chat_id: int,
        update_data: UserUpdate,
    ) -> UserResponse:
        """
        تحديث مستخدم.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            update_data: بيانات التحديث
            
        Returns:
            UserResponse: بيانات المستخدم المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المستخدم
        """
        logger.info(
            "user_service_update",
            extra={
                "chat_id": chat_id,
                "fields": list(update_data.model_dump(exclude_unset=True).keys()),
            },
        )

        # التحقق من وجود المستخدم
        user = await self.repo.get_by_chat_id(
            chat_id=chat_id,
        )

        if not user:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        # تحضير بيانات التحديث
        updates = update_data.model_dump(exclude_unset=True)

        # تنظيف البيانات
        if "customer_name" in updates:
            updates["customer_name"] = sanitize_input(updates["customer_name"])

        if "customer_phone" in updates:
            updates["customer_phone"] = sanitize_input(updates["customer_phone"])

        # تحديث المستخدم
        updated = await self.repo.update(
            id=user.id,
            data=updates,
        )

        if not updated:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        logger.info(
            "user_updated_successfully",
            extra={
                "user_id": updated.id,
                "chat_id": chat_id,
            },
        )

        return UserResponse.model_validate(updated)

    # ==============================================
    # UPDATE NAME
    # ==============================================

    async def update_name(
        self,
        *,
        chat_id: int,
        customer_name: str,
    ) -> UserResponse:
        """
        تحديث اسم العميل.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            customer_name: اسم العميل الجديد
            
        Returns:
            UserResponse: بيانات المستخدم المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المستخدم
        """
        clean_name = sanitize_input(customer_name)

        logger.info(
            "user_service_update_name",
            extra={
                "chat_id": chat_id,
                "customer_name": clean_name,
            },
        )

        if not clean_name:
            raise ValidationError(
                message="اسم العميل مطلوب",
            )

        user = await self.repo.update_name(
            chat_id=chat_id,
            customer_name=clean_name,
        )

        if not user:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        logger.info(
            "user_name_updated_successfully",
            extra={
                "user_id": user.id,
                "chat_id": chat_id,
            },
        )

        return UserResponse.model_validate(user)

    # ==============================================
    # UPDATE PHONE
    # ==============================================

    async def update_phone(
        self,
        *,
        chat_id: int,
        customer_phone: str,
    ) -> UserResponse:
        """
        تحديث رقم هاتف العميل.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            customer_phone: رقم الهاتف الجديد
            
        Returns:
            UserResponse: بيانات المستخدم المحدث
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المستخدم
        """
        clean_phone = sanitize_input(customer_phone)

        logger.info(
            "user_service_update_phone",
            extra={
                "chat_id": chat_id,
                "customer_phone": clean_phone,
            },
        )

        if not clean_phone:
            raise ValidationError(
                message="رقم الهاتف مطلوب",
            )

        user = await self.repo.update_phone(
            chat_id=chat_id,
            customer_phone=clean_phone,
        )

        if not user:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        logger.info(
            "user_phone_updated_successfully",
            extra={
                "user_id": user.id,
                "chat_id": chat_id,
            },
        )

        return UserResponse.model_validate(user)

    # ==============================================
    # DELETE USER
    # ==============================================

    async def delete_user(
        self,
        *,
        chat_id: int,
    ) -> None:
        """
        حذف مستخدم.
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            
        Raises:
            NotFoundError: إذا لم يتم العثور على المستخدم
        """
        logger.info(
            "user_service_delete",
            extra={"chat_id": chat_id},
        )

        user = await self.repo.get_by_chat_id(
            chat_id=chat_id,
        )

        if not user:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        deleted = await self.repo.delete(id=user.id)

        if not deleted:
            raise NotFoundError(
                message=f"المستخدم بـ chat_id '{chat_id}' غير موجود",
            )

        logger.info(
            "user_deleted_successfully",
            extra={
                "user_id": user.id,
                "chat_id": chat_id,
            },
        )

    # ==========================================
    # 🔄 UPSERT USER
    # ==========================================

    # ==============================================
    # UPSERT USER
    # ==============================================

    async def upsert_user(
        self,
        *,
        chat_id: int,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        consent: bool = False,
    ) -> UserResponse:
        """
        إنشاء أو تحديث مستخدم (Upsert).
        
        Args:
            chat_id: معرف المستخدم في تيليجرام
            customer_name: اسم العميل (اختياري)
            customer_phone: رقم هاتف العميل (اختياري)
            consent: حالة الموافقة
            
        Returns:
            UserResponse: بيانات المستخدم المنشأ أو المحدث
        """
        logger.info(
            "user_service_upsert",
            extra={
                "chat_id": chat_id,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
            },
        )

        # تنظيف البيانات
        clean_name = sanitize_input(customer_name) if customer_name else None
        clean_phone = sanitize_input(customer_phone) if customer_phone else None

        user = await self.repo.get_by_chat_id(
            chat_id=chat_id,
        )

        if user:
            # تحديث المستخدم الموجود
            data: UserUpdateData = {}

            if clean_name is not None:
                data["customer_name"] = clean_name

            if clean_phone is not None:
                data["customer_phone"] = clean_phone

            if consent is not None:
                data["consent"] = consent

            if data:
                user = await self.repo.update(
                    id=user.id,
                    data=data,
                )

            logger.info(
                "user_updated_by_upsert",
                extra={
                    "user_id": user.id,
                    "chat_id": chat_id,
                },
            )
        else:
            # إنشاء مستخدم جديد
            data: UserData = {
                "chat_id": chat_id,
                "consent": consent,
            }

            if clean_name is not None:
                data["customer_name"] = clean_name

            if clean_phone is not None:
                data["customer_phone"] = clean_phone

            user = await self.repo.create(data=data)

            logger.info(
                "user_created_by_upsert",
                extra={
                    "user_id": user.id,
                    "chat_id": chat_id,
                },
            )

        return UserResponse.model_validate(user)

    # ==========================================
    # 📊 STATISTICS
    # ==========================================

    # ==============================================
    # GET USER STATS
    # ==============================================

    async def get_user_stats(
        self,
    ) -> UserSummary:
        """
        الحصول على إحصائيات المستخدمين.
        
        Returns:
            UserSummary: إحصائيات المستخدمين
        """
        logger.info("user_service_get_stats")

        total_users = await self.repo.count()
        users_with_consent = await self.repo.count_with_consent()
        users_without_consent = await self.repo.count_without_consent()
        users_with_name = await self.repo.count_with_name()
        users_with_phone = await self.repo.count_with_phone()

        consent_rate = (users_with_consent / total_users * 100) if total_users > 0 else 0

        return UserSummary(
            total_users=total_users,
            users_with_consent=users_with_consent,
            users_without_consent=users_without_consent,
            users_with_name=users_with_name,
            users_with_phone=users_with_phone,
            consent_rate=round(consent_rate, 2),
        )


# ==============================================
# 🔄 COMPATIBILITY FUNCTIONS
# دوال متوافقة مع الاستيرادات القديمة
# ==============================================

# ==============================================
# GET OR CREATE USER (COMPATIBILITY)
# ==============================================

async def get_or_create_user(
    *,
    chat_id: int,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
    consent: bool = False,
    session: AsyncSession,
) -> int:
    """
    الحصول على مستخدم أو إنشاؤه (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        customer_name: اسم العميل (اختياري)
        customer_phone: رقم هاتف العميل (اختياري)
        consent: حالة الموافقة
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف المستخدم
    """
    service = UserService(session=session)

    user = await service.upsert_user(
        chat_id=chat_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        consent=consent,
    )

    return user.id


# ==============================================
# GET USER (COMPATIBILITY)
# ==============================================

async def get_user(
    *,
    chat_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مستخدم بواسطة chat_id (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        Optional[Dict[str, Any]]: قاموس بيانات المستخدم أو None
    """
    service = UserService(session=session)

    user = await service.get_by_chat_id(chat_id=chat_id)

    if not user:
        return None

    return user.model_dump()


# ==============================================
# HAS USER CONSENT (COMPATIBILITY)
# ==============================================

async def has_user_consent(
    *,
    chat_id: int,
    session: AsyncSession,
) -> bool:
    """
    التحقق من موافقة المستخدم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        bool: True إذا كان لديه موافقة
    """
    service = UserService(session=session)

    return await service.has_consent(chat_id=chat_id)


# ==============================================
# GIVE USER CONSENT (COMPATIBILITY)
# ==============================================

async def give_user_consent(
    *,
    chat_id: int,
    session: AsyncSession,
) -> int:
    """
    منح موافقة المستخدم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        int: معرف المستخدم
    """
    service = UserService(session=session)

    user = await service.give_consent(chat_id=chat_id)

    return user.id


# ==============================================
# REVOKE USER CONSENT (COMPATIBILITY)
# ==============================================

async def revoke_user_consent(
    *,
    chat_id: int,
    session: AsyncSession,
) -> None:
    """
    إلغاء موافقة المستخدم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على المستخدم
    """
    service = UserService(session=session)

    await service.revoke_consent(chat_id=chat_id)

    logger.info(
        "user_consent_revoked",
        extra={"chat_id": chat_id},
    )


# ==============================================
# UPDATE USER NAME (COMPATIBILITY)
# ==============================================

async def update_user_name(
    *,
    chat_id: int,
    customer_name: str,
    session: AsyncSession,
) -> None:
    """
    تحديث اسم المستخدم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        customer_name: اسم العميل الجديد
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على المستخدم
    """
    service = UserService(session=session)

    await service.update_name(
        chat_id=chat_id,
        customer_name=customer_name,
    )

    logger.info(
        "user_name_updated",
        extra={"chat_id": chat_id},
    )


# ==============================================
# UPDATE USER PHONE (COMPATIBILITY)
# ==============================================

async def update_user_phone(
    *,
    chat_id: int,
    customer_phone: str,
    session: AsyncSession,
) -> None:
    """
    تحديث رقم هاتف المستخدم (دالة متوافقة مع الإصدار القديم).
    
    Args:
        chat_id: معرف المستخدم في تيليجرام
        customer_phone: رقم الهاتف الجديد
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Raises:
        NotFoundError: إذا لم يتم العثور على المستخدم
    """
    service = UserService(session=session)

    await service.update_phone(
        chat_id=chat_id,
        customer_phone=customer_phone,
    )

    logger.info(
        "user_phone_updated",
        extra={"chat_id": chat_id},
    )
