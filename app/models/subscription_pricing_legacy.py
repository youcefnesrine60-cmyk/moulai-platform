# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# EXPLICIT PRE-O3 COMPATIBILITY MAPPING
# Historical S1/O2 fixtures and unmigrated review reads use the same physical singleton only before cutover.
# ==============================================

"""Never selected by the O3/O4 country-version path; creates no table or second store."""

from sqlalchemy import (
    JSON,
    Column,
    Integer,
    MetaData,
    Numeric,
)

from app.models.base import Base

# ==============================================
# ISOLATED LEGACY METADATA
# Exclude the removed price column from the current application's global metadata.
# ==============================================


class LegacySubscriptionPricingConfig(Base):
    """Compatibility with physically unmigrated profiles, not an O3 pricing authority."""

    metadata = MetaData()
    __tablename__ = "subscription_pricing_config"
    id = Column(Integer, primary_key=True)
    base_price = Column(Numeric(14, 2), nullable=False)
    policies = Column(JSON, nullable=False)
