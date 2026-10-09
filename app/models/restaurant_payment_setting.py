# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTING MODEL
# نموذج إعدادات الدفع للمطعم
# ==============================================

"""MoulAI operational module for restaurant payment setting.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel

# ==============================================
# 🧩 TYPES
# ==============================================

AllowedMethodsList = List[str]

# ==============================================
# 🏦 RESTAURANT PAYMENT SETTING
# ==============================================


class RestaurantPaymentSetting(BaseModel):
    """
    نموذج إعدادات الدفع للمطعم.

    يدير طرق الدفع المسموح بها لكل مطعم.

    Attributes:
        restaurant_id: معرف المطعم (ForeignKey, Unique)
        allow_cash: السماح بالدفع نقداً
        allow_card: السماح بالدفع ببطاقة POS
        allow_ccp: السماح بالدفع عبر CCP
        allow_baridimob: السماح بالدفع عبر بريدي موب
        allow_stripe: السماح بالدفع عبر Stripe
        allow_paypal: السماح بالدفع عبر PayPal
        restaurant: علاقة مع نموذج Restaurant
    """

    __tablename__ = "restaurant_payment_settings"

    # ==========================================
    # 🗂️ COLUMNS
    # ==========================================

    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="معرف المطعم",
    )
    allow_cash = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="السماح بالدفع نقداً",
    )
    allow_card = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="السماح بالدفع ببطاقة POS",
    )
    allow_ccp = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="السماح بالدفع عبر CCP",
    )
    allow_baridimob = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="السماح بالدفع عبر بريدي موب",
    )
    allow_stripe = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="السماح بالدفع عبر Stripe",
    )
    allow_paypal = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="السماح بالدفع عبر PayPal",
    )

    # ==========================================
    # 🔒 CONSTRAINTS
    # ==========================================

    __table_args__ = (
        UniqueConstraint(
            "restaurant_id",
            name="uq_restaurant_payment_settings",
            comment="تأكد من وجود إعدادات دفع واحدة فقط لكل مطعم",
        ),
    )

    # ==========================================
    # 🔗 RELATIONSHIPS
    # ==========================================

    restaurant = relationship(
        "Restaurant",
        back_populates="payment_settings",
        lazy="selectin",
        # comment="المطعم المرتبط",
    )

    # ==========================================
    # 📝 REPRESENTATION
    # ==========================================

    def __repr__(self) -> str:
        """
        تمثيل نصي للنموذج.

        Returns:
            سلسلة نصية تحتوي على معرف المطعم وحالتَي النقد والبطاقة
        """
        return (
            f"<RestaurantPaymentSetting(restaurant_id={self.restaurant_id}, "
            f"cash={self.allow_cash}, card={self.allow_card})>"
        )

    # ==========================================
    # 🛠️ HELPER METHODS
    # ==========================================

    # ==============================================
    # GET ALLOWED METHODS
    # ==============================================

    def get_allowed_methods(self) -> AllowedMethodsList:
        """
        الحصول على قائمة طرق الدفع المسموح بها.

        Returns:
            قائمة طرق الدفع المسموح بها
        """
        allowed: AllowedMethodsList = []

        if self.allow_cash:
            allowed.append("cash")
        if self.allow_card:
            allowed.append("card")
        if self.allow_ccp:
            allowed.append("ccp")
        if self.allow_baridimob:
            allowed.append("baridimob")
        if self.allow_stripe:
            allowed.append("stripe")
        if self.allow_paypal:
            allowed.append("paypal")

        return allowed

    # ==============================================
    # IS METHOD ALLOWED
    # ==============================================

    def is_method_allowed(self, method: str) -> bool:
        """
        التحقق من أن طريقة دفع معينة مسموح بها.

        Args:
            method: طريقة الدفع (cash, card, ccp, baridimob, stripe, paypal)

        Returns:
            True إذا كانت مسموحة، False إذا لم تكن
        """
        method_lower = method.lower()

        method_map = {
            "cash": self.allow_cash,
            "card": self.allow_card,
            "ccp": self.allow_ccp,
            "baridimob": self.allow_baridimob,
            "stripe": self.allow_stripe,
            "paypal": self.allow_paypal,
        }

        return method_map.get(method_lower, False)
