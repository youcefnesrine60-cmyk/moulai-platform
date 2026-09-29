# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🎛 OPTION GROUPS REPOSITORY
# عمليات قاعدة البيانات لمجموعات الخيارات باستخدام SQLAlchemy
# ==============================================

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import logger
from app.models.option_group import OptionGroup
from app.repositories.base import BaseRepository

# ==============================================
# 🧩 TYPES
# ==============================================

OptionGroupData = Dict[str, Any]
OptionGroupUpdateData = Dict[str, Any]
OptionGroupList = List[OptionGroup]

# ==============================================
# 🎛 OPTION GROUPS REPOSITORY
# ==============================================


class OptionGroupsRepository(
    BaseRepository[
        OptionGroup,
        OptionGroupData,
        OptionGroupUpdateData,
    ]
):
    """
    مستودع مجموعات الخيارات - يوفر عمليات خاصة بمجموعات الخيارات.
    
    مسؤول عن:
        - عمليات CRUD الأساسية لمجموعات الخيارات
        - البحث والتصفية حسب المنتج
        - جلب مجموعات الخيارات مع خياراتها
    
    Attributes:
        model: نموذج OptionGroup
        session: جلسة قاعدة البيانات غير المتزامنة
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        تهيئة مستودع مجموعات الخيارات.
        
        Args:
            session: جلسة قاعدة البيانات غير المتزامنة
        """
        super().__init__(OptionGroup, session)

    # ==========================================
    # 📖 QUERIES
    # ==========================================

    # ==============================================
    # GET BY PRODUCT ID
    # ==============================================

    async def get_by_product_id(
        self,
        *,
        product_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> OptionGroupList:
        """
        الحصول على مجموعات خيارات منتج معين.
        
        Args:
            product_id: معرف المنتج
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة مجموعات الخيارات
        """
        try:
            query = (
                select(self.model)
                .where(self.model.product_id == product_id)
                .order_by(self.model.sort_order.asc(), self.model.id.asc())
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "option_groups_repo_get_by_product_failed",
                extra={
                    "product_id": product_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET BY NAME
    # ==============================================

    async def get_by_name(
        self,
        *,
        product_id: int,
        name: str,
    ) -> Optional[OptionGroup]:
        """
        الحصول على مجموعة خيارات بواسطة اسمها.
        
        Args:
            product_id: معرف المنتج
            name: اسم مجموعة الخيارات
            
        Returns:
            كائن OptionGroup أو None
        """
        try:
            result = await self.session.execute(
                select(self.model)
                .where(
                    self.model.product_id == product_id,
                    self.model.name == name,
                )
                .limit(1),
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "option_groups_repo_get_by_name_failed",
                extra={
                    "product_id": product_id,
                    "option_groups_name": name,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET WITH OPTIONS
    # ==============================================

    async def get_with_options(
        self,
        *,
        group_id: int,
    ) -> Optional[OptionGroup]:
        """
        الحصول على مجموعة خيارات مع خياراتها.
        
        Args:
            group_id: معرف مجموعة الخيارات
            
        Returns:
            كائن OptionGroup مع الخيارات أو None
        """
        try:
            query = (
                select(self.model)
                .where(self.model.id == group_id)
                .options(selectinload(self.model.options))
            )

            result = await self.session.execute(query)

            return result.scalar_one_or_none()

        except Exception as e:
            logger.exception(
                "option_groups_repo_get_with_options_failed",
                extra={
                    "group_id": group_id,
                    "error": str(e),
                },
            )
            raise

    # ==============================================
    # GET REQUIRED BY PRODUCT
    # ==============================================

    async def get_required_by_product(
        self,
        *,
        product_id: int,
    ) -> OptionGroupList:
        """
        الحصول على مجموعات الخيارات الإجبارية لمنتج معين.
        
        Args:
            product_id: معرف المنتج
            
        Returns:
            قائمة مجموعات الخيارات الإجبارية
        """
        try:
            query = (
                select(self.model)
                .where(
                    self.model.product_id == product_id,
                    self.model.required == True,
                )
                .order_by(self.model.sort_order.asc())
            )

            result = await self.session.execute(query)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "option_groups_repo_get_required_by_product_failed",
                extra={
                    "product_id": product_id,
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
        product_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> OptionGroupList:
        """
        البحث عن مجموعات خيارات.
        
        Args:
            query: نص البحث
            product_id: معرف المنتج (اختياري)
            skip: عدد السجلات للتخطي
            limit: الحد الأقصى للسجلات
            
        Returns:
            قائمة مجموعات الخيارات
        """
        try:
            conditions = [
                self.model.name.ilike(f"%{query}%"),
            ]

            if product_id is not None:
                conditions.append(
                    self.model.product_id == product_id,
                )

            stmt = (
                select(self.model)
                .where(*conditions)
                .order_by(
                    self.model.sort_order.asc(),
                    self.model.name.asc(),
                )
                .offset(skip)
                .limit(limit)
            )

            result = await self.session.execute(stmt)

            return result.scalars().all()

        except Exception as e:
            logger.exception(
                "option_groups_repo_search_failed",
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
    # UPDATE SORT ORDER
    # ==============================================

    async def update_sort_order(
        self,
        *,
        group_id: int,
        sort_order: int,
    ) -> Optional[OptionGroup]:
        """
        تحديث ترتيب مجموعة الخيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            sort_order: الترتيب الجديد
            
        Returns:
            كائن OptionGroup المحدث أو None
        """
        logger.info(
            "option_groups_repo_update_sort_order",
            extra={
                "group_id": group_id,
                "sort_order": sort_order,
            },
        )

        return await self.update(
            id=group_id,
            data={"sort_order": sort_order},
        )

    # ==============================================
    # UPDATE REQUIRED
    # ==============================================

    async def update_required(
        self,
        *,
        group_id: int,
        required: bool,
    ) -> Optional[OptionGroup]:
        """
        تحديث حالة الإجبار لمجموعة الخيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            required: حالة الإجبار الجديدة
            
        Returns:
            كائن OptionGroup المحدث أو None
        """
        logger.info(
            "option_groups_repo_update_required",
            extra={
                "group_id": group_id,
                "required": required,
            },
        )

        return await self.update(
            id=group_id,
            data={"required": required},
        )

    # ==============================================
    # UPDATE MULTIPLE CHOICE
    # ==============================================

    async def update_multiple_choice(
        self,
        *,
        group_id: int,
        multiple_choice: bool,
    ) -> Optional[OptionGroup]:
        """
        تحديث حالة الاختيار المتعدد لمجموعة الخيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            multiple_choice: حالة الاختيار المتعدد الجديدة
            
        Returns:
            كائن OptionGroup المحدث أو None
        """
        logger.info(
            "option_groups_repo_update_multiple_choice",
            extra={
                "group_id": group_id,
                "multiple_choice": multiple_choice,
            },
        )

        return await self.update(
            id=group_id,
            data={"multiple_choice": multiple_choice},
        )

    # ==============================================
    # UPDATE NAME
    # ==============================================

    async def update_name(
        self,
        *,
        group_id: int,
        name: str,
    ) -> Optional[OptionGroup]:
        """
        تحديث اسم مجموعة الخيارات.
        
        Args:
            group_id: معرف مجموعة الخيارات
            name: الاسم الجديد
            
        Returns:
            كائن OptionGroup المحدث أو None
        """
        logger.info(
            "option_groups_repo_update_name",
            extra={
                "group_id": group_id,
                "option_groups_name": name,
            },
        )

        return await self.update(
            id=group_id,
            data={"name": name},
        )

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
            عدد مجموعات الخيارات
        """
        return await self.count(filters={"product_id": product_id})

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
            عدد مجموعات الخيارات الإجبارية
        """
        return await self.count(
            filters={
                "product_id": product_id,
                "required": True,
            },
        )

    # ==========================================
    # 🗑️ DELETE
    # ==========================================

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
            عدد المجموعات المحذوفة
        """
        try:
            # جلب جميع المجموعات
            groups = await self.get_by_product_id(
                product_id=product_id,
            )

            count = len(groups)

            # حذف كل مجموعة
            for group in groups:
                await self.delete(id=group.id)

            logger.info(
                "option_groups_deleted_by_product",
                extra={
                    "product_id": product_id,
                    "count": count,
                },
            )

            return count

        except Exception as e:
            logger.exception(
                "option_groups_repo_delete_by_product_failed",
                extra={
                    "product_id": product_id,
                    "error": str(e),
                },
            )
            raise


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
        معرف مجموعة الخيارات
    """
    repo = OptionGroupsRepository(session=session)

    data: OptionGroupData = {
        "product_id": product_id,
        "name": name,
        "required": required,
        "multiple_choice": multiple_choice,
        "sort_order": sort_order,
    }

    group = await repo.create(data=data)

    logger.info(
        "option_group_created",
        extra={
            "group_id": group.id,
            "product_id": product_id,
        },
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
        قاموس بيانات مجموعة الخيارات أو None
    """
    repo = OptionGroupsRepository(session=session)

    group = await repo.get_by_id(id=group_id)

    if not group:
        return None

    return {
        "id": group.id,
        "product_id": group.product_id,
        "name": group.name,
        "required": group.required,
        "multiple_choice": group.multiple_choice,
        "sort_order": group.sort_order,
        "created_at": group.created_at,
    }


# ==============================================
# GET PRODUCT OPTION GROUPS (COMPATIBILITY)
# ==============================================

async def get_product_option_groups(
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
        قائمة مجموعات الخيارات
    """
    repo = OptionGroupsRepository(session=session)

    groups = await repo.get_by_product_id(
        product_id=product_id,
        skip=skip,
        limit=limit,
    )

    result = []

    for group in groups:
        result.append({
            "id": group.id,
            "product_id": group.product_id,
            "name": group.name,
            "required": group.required,
            "multiple_choice": group.multiple_choice,
            "sort_order": group.sort_order,
            "created_at": group.created_at,
        })

    return result


# ==============================================
# GET OPTION GROUP WITH OPTIONS (COMPATIBILITY)
# ==============================================

async def get_option_group_with_options(
    *,
    group_id: int,
    session: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    الحصول على مجموعة خيارات مع خياراتها (دالة متوافقة مع الإصدار القديم).
    
    Args:
        group_id: معرف مجموعة الخيارات
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قاموس بيانات مجموعة الخيارات مع الخيارات أو None
    """
    repo = OptionGroupsRepository(session=session)

    group = await repo.get_with_options(group_id=group_id)

    if not group:
        return None

    return {
        "id": group.id,
        "product_id": group.product_id,
        "name": group.name,
        "required": group.required,
        "multiple_choice": group.multiple_choice,
        "sort_order": group.sort_order,
        "created_at": group.created_at,
        "options": [
            {
                "id": option.id,
                "name": option.name,
                "extra_price": option.extra_price,
                "is_available": option.is_available,
                "sort_order": option.sort_order,
            }
            for option in group.options
        ],
    }


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
    """
    repo = OptionGroupsRepository(session=session)

    await repo.delete(id=group_id)

    logger.info(
        "option_group_deleted",
        extra={"group_id": group_id},
    )


# ==============================================
# GET REQUIRED OPTION GROUPS (COMPATIBILITY)
# ==============================================

async def get_required_option_groups(
    *,
    product_id: int,
    session: AsyncSession,
) -> List[Dict[str, Any]]:
    """
    الحصول على مجموعات الخيارات الإجبارية لمنتج معين (دالة متوافقة مع الإصدار القديم).
    
    Args:
        product_id: معرف المنتج
        session: جلسة قاعدة البيانات غير المتزامنة
        
    Returns:
        قائمة مجموعات الخيارات الإجبارية
    """
    repo = OptionGroupsRepository(session=session)

    groups = await repo.get_required_by_product(product_id=product_id)

    result = []

    for group in groups:
        result.append({
            "id": group.id,
            "product_id": group.product_id,
            "name": group.name,
            "required": group.required,
            "multiple_choice": group.multiple_choice,
            "sort_order": group.sort_order,
            "created_at": group.created_at,
        })

    return result