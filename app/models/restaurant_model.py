# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / MODELS / RESTAURANT MODEL
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for restaurant model.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from pydantic import BaseModel

# ==============================================
# ➕ CREATE RESTAURANT
# ==============================================


class RestaurantCreate(
    BaseModel,
):

    name: str

    owner: str

    type: str

    phone: str

    wilaya: str

    lat: float

    lng: float

    chat_id: int
