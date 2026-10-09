# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# MOULAI MODULE - APP / STATES / TRANSITIONS
# Operational component of the MoulAI platform.
# ==============================================

"""MoulAI operational module for transitions.

Part of MoulAI Platform - Agent-as-a-Service.
"""

from app.states.owner_states import OwnerStates

ALLOWED_TRANSITIONS = {
    OwnerStates.NAME: [OwnerStates.RESTAURANT],
    OwnerStates.RESTAURANT: [OwnerStates.WILAYA],
    OwnerStates.WILAYA: [OwnerStates.LOCATION],
    OwnerStates.LOCATION: [OwnerStates.TYPE],
    OwnerStates.TYPE: [OwnerStates.PHONE],
    OwnerStates.PHONE: [OwnerStates.CONFIRM],
}
