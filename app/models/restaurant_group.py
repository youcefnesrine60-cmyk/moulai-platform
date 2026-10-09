# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏢 RESTAURANT GROUP MODEL
# نموذج مجموعة المطاعم
# يدير مجموعات المطاعم التابعة للمالكين وعلاقاتها بالفروع
# ==============================================

"""MoulAI operational module for restaurant group.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 🏢 RESTAURANT GROUP
# ==============================================


class RestaurantGroup(BaseModel):
    """
    نموذج مجموعة المطاعم

    يدير:
        - مجموعات المطاعم التابعة للمالكين
        - اسم المجموعة
        - العلاقات مع المالك والمطاعم والفروع

    Attributes:
        owner_id: معرف المالك (ForeignKey)
        name: اسم المجموعة
        owner: علاقة مع نموذج Owner
        restaurants: قائمة المطاعم التابعة للمجموعة
        branch_links: قائمة روابط الفروع
    """

    __tablename__ = "restaurant_groups"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    owner_id = Column(
        Integer,
        ForeignKey("owners.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المالك",
    )
    name = Column(
        String(255),
        nullable=False,
        comment="اسم المجموعة",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    owner = relationship(
        "Owner",
        back_populates="restaurant_groups",
        lazy="selectin",
        # comment="المالك",
    )
    restaurants = relationship(
        "Restaurant",
        back_populates="group",
        lazy="selectin",
        # comment="قائمة المطاعم التابعة للمجموعة",
    )
    branch_links = relationship(
        "RestaurantBranch",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
        # comment="قائمة روابط الفروع",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على المعرف والاسم ومعرف المالك
        """
        return (
            f"<RestaurantGroup(id={self.id}, name={self.name}, "
            f"owner_id={self.owner_id})>"
        )


# ==============================================
# 🔗 RESTAURANT BRANCH
# رابط فرع المطعم
# ==============================================


class RestaurantBranch(BaseModel):
    """
    نموذج رابط فرع المطعم

    يربط المطاعم بمجموعات المطاعم.

    Attributes:
        group_id: معرف المجموعة (ForeignKey)
        restaurant_id: معرف المطعم (ForeignKey)
        group: علاقة مع نموذج RestaurantGroup
        restaurant: علاقة مع نموذج Restaurant
    """

    __tablename__ = "restaurant_branches"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    group_id = Column(
        Integer,
        ForeignKey("restaurant_groups.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المجموعة",
    )
    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        comment="معرف المطعم",
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    group = relationship(
        "RestaurantGroup",
        back_populates="branch_links",
        lazy="selectin",
        # comment="المجموعة",
    )
    restaurant = relationship(
        "Restaurant",
        lazy="selectin",
        # comment="المطعم",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج

        Returns:
            سلسلة نصية تحتوي على معرف المجموعة ومعرف المطعم
        """
        return (
            f"<RestaurantBranch(group_id={self.group_id}, "
            f"restaurant_id={self.restaurant_id})>"
        )
