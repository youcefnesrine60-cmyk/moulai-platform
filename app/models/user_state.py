# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / MODELS / USER STATE
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for user state.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from typing import Optional

from pydantic import BaseModel, Field

# ==============================================
# 🧠 USER STATE
# ==============================================


class UserState(
    BaseModel,
):

    step: str

    history: list[str] = Field(
        default_factory=list,
    )

    owner: Optional[str] = None

    restaurant: Optional[str] = None

    wilaya: Optional[str] = None

    lat: Optional[float] = None

    lng: Optional[float] = None

    type: Optional[str] = None

    phone: Optional[str] = None
