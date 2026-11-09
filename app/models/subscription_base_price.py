# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# COUNTRY AND CURRENCY BASE VERSION MODEL
# Map O3's single authoritative price store without changing the retained O2 ORM contract.
# ==============================================

"""Prepared O3 mapping; importing this file creates no database objects."""

from __future__ import annotations

# isort: split
# ==============================================
# EXACT PERSISTENCE TYPES
# Keep decimal money, UTC validity and author references independent from live accounts.
# ==============================================

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.models.base import Base

# ==============================================
# RETAINED COUNTRY BASE DECISION
# A row is never repriced; replacement closes its interval and inserts another revision.
# ==============================================


class SubscriptionBasePrice(Base):
    """O3 price version; database DDL owns exclusion and immutability constraints."""

    __tablename__ = "subscription_base_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(2))
    currency: Mapped[str] = mapped_column(String(3))
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    revision: Mapped[str] = mapped_column(String(128), unique=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.transaction_timestamp()
    )
    author_admin_id: Mapped[int | None] = mapped_column(Integer)
    source_reference: Mapped[str] = mapped_column(Text)
